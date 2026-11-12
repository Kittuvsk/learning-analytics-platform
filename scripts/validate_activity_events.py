
import sqlite3
from pathlib import Path

import pandas as pd

from app.generation.config import (
    GENERATED_DIR,
    GROUND_TRUTH_DIR,
    PROCESSED_DIR,
)


EVENT_FILE = GENERATED_DIR / "activity_events.csv"
GROUND_TRUTH_FILE = GROUND_TRUTH_DIR / "ground_truth.csv"
ENROLLMENT_FILE = GENERATED_DIR / "enrollments.csv"
LEARNER_FILE = GENERATED_DIR / "learners.csv"
COURSE_FILE = GENERATED_DIR / "courses.csv"
CONTENT_FILE = GENERATED_DIR / "content_items.csv"
ATTEMPT_FILE = GENERATED_DIR / "attempts.csv"

EXPECTED_EVENTS = 2_000_000
EXPECTED_ANOMALIES = 20_000
CHUNK_SIZE = 100_000

VALID_EVENT_TYPES = {
    "COURSE_OPENED", "CONTENT_VIEWED", "VIDEO_PLAYED",
    "VIDEO_COMPLETED", "DOCUMENT_DOWNLOADED",
    "QUIZ_STARTED", "QUIZ_SUBMITTED",
    "ASSIGNMENT_SUBMITTED", "COURSE_COMPLETED",
    "LOGIN", "OTHER",
}

VALID_DEVICES = {"DESKTOP", "MOBILE", "TABLET", "OTHER"}
VALID_SYNC_TYPES = {"ONLINE", "OFFLINE_SYNC"}

VALID_ISSUES = {
    "DUPLICATE_EVENT",
    "UNENROLLED_ACTIVITY",
    "PREMATURE_COMPLETION",
    "TIMEZONE_MISALIGNMENT",
}


def main():

    print("Loading reference data...")

    enrollments = pd.read_csv(ENROLLMENT_FILE)
    learners = pd.read_csv(LEARNER_FILE)
    courses = pd.read_csv(COURSE_FILE)
    content = pd.read_csv(CONTENT_FILE)
    attempts = pd.read_csv(ATTEMPT_FILE)
    ground_truth = pd.read_csv(GROUND_TRUTH_FILE)

    for column in ["enrolled_at", "withdrawn_at"]:
        enrollments[column] = pd.to_datetime(
            enrollments[column], errors="coerce"
        )

    attempts["started_at"] = pd.to_datetime(
        attempts["started_at"], errors="coerce"
    )

    enrollment_learner = enrollments.set_index(
        "enrollment_id"
    )["learner_id"].to_dict()

    enrollment_course = enrollments.set_index(
        "enrollment_id"
    )["course_id"].to_dict()

    enrollment_start = enrollments.set_index(
        "enrollment_id"
    )["enrolled_at"].to_dict()

    enrollment_status = enrollments.set_index(
        "enrollment_id"
    )["enrollment_status"].to_dict()

    withdrawn_at = enrollments.set_index(
        "enrollment_id"
    )["withdrawn_at"].to_dict()

    learner_ids = set(learners["learner_id"])
    course_ids = set(courses["course_id"])

    content_course = content.set_index(
        "content_item_id"
    )["course_id"].to_dict()

    existing_pairs = set(
        zip(enrollments["learner_id"], enrollments["course_id"])
    )

    earliest_attempt = (
        attempts.groupby("enrollment_id")["started_at"]
        .min()
        .to_dict()
    )

    print("Reference data loaded.")

    # -------------------------------------------------
    # GROUND TRUTH VALIDATION
    # -------------------------------------------------

    print("\nValidating ground truth...")

    if len(ground_truth) != EXPECTED_ANOMALIES:
        raise ValueError(
            f"Expected {EXPECTED_ANOMALIES} ground-truth rows, "
            f"found {len(ground_truth)}"
        )

    if ground_truth["entity_id"].duplicated().any():
        raise ValueError("Duplicate ground-truth entity IDs")

    if not set(ground_truth["issue_type"]).issubset(VALID_ISSUES):
        raise ValueError("Unknown anomaly type in ground truth")

    if not (ground_truth["expected_label"] == 1).all():
        raise ValueError("Unexpected ground-truth label")

    issue_counts = ground_truth["issue_type"].value_counts()

    for issue in VALID_ISSUES:
        if issue_counts.get(issue, 0) != 5_000:
            raise ValueError(
                f"Expected 5,000 labels for {issue}"
            )

    truth_map = ground_truth.set_index(
        "entity_id"
    )["issue_type"].to_dict()

    duplicate_expected = (
        ground_truth[
            ground_truth["issue_type"] == "DUPLICATE_EVENT"
        ]
        .set_index("entity_id")["expected_value"]
        .to_dict()
    )

    timezone_expected = (
        ground_truth[
            ground_truth["issue_type"] == "TIMEZONE_MISALIGNMENT"
        ]
        .set_index("entity_id")["expected_value"]
        .to_dict()
    )

    print("Ground-truth validation: PASSED")

    # -------------------------------------------------
    # DISK-BACKED EVENT ID UNIQUENESS CHECK
    # -------------------------------------------------

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    sqlite_file = PROCESSED_DIR / "event_id_validation.sqlite"

    if sqlite_file.exists():
        sqlite_file.unlink()

    connection = sqlite3.connect(sqlite_file)

    connection.execute(
        "CREATE TABLE event_ids (event_id TEXT PRIMARY KEY)"
    )

    total_rows = 0
    found_truth_ids = set()

    issue_found = {issue: 0 for issue in VALID_ISSUES}

    print("\nStarting streaming event validation...")

    try:

        for chunk_number, chunk in enumerate(
            pd.read_csv(
                EVENT_FILE,
                chunksize=CHUNK_SIZE,
                dtype={
                    "event_id": "string",
                    "learner_id": "string",
                    "course_id": "string",
                    "enrollment_id": "string",
                    "event_type": "string",
                    "learner_timezone": "string",
                    "device_type": "string",
                    "sync_type": "string",
                    "source_event_id": "string",
                },
            ),
            start=1,
        ):

            chunk["enrollment_id"] = chunk[
                "enrollment_id"
            ].replace("", pd.NA)

            # Required values.
            required_columns = [
                "event_id",
                "learner_id",
                "course_id",
                "event_type",
                "event_time_utc",
                "received_at_utc",
                "learner_timezone",
                "device_type",
                "sync_type",
                "duration_seconds",
                "is_late_event",
            ]

            if chunk[required_columns].isna().any().any():
                raise ValueError(
                    f"Missing required values in chunk {chunk_number}"
                )

            # Primary key uniqueness.
            before = connection.total_changes

            connection.executemany(
                "INSERT OR IGNORE INTO event_ids(event_id) VALUES (?)",
                [(value,) for value in chunk["event_id"]],
            )

            inserted = connection.total_changes - before

            if inserted != len(chunk):
                raise ValueError(
                    f"Duplicate event IDs found in chunk {chunk_number}"
                )

            # Learner and course foreign keys.
            if not chunk["learner_id"].isin(learner_ids).all():
                raise ValueError(
                    f"Invalid learner reference in chunk {chunk_number}"
                )

            if not chunk["course_id"].isin(course_ids).all():
                raise ValueError(
                    f"Invalid course reference in chunk {chunk_number}"
                )

            # Event, device and synchronization enums.
            if not set(chunk["event_type"]).issubset(
                VALID_EVENT_TYPES
            ):
                raise ValueError("Invalid event type")

            if not set(chunk["device_type"]).issubset(
                VALID_DEVICES
            ):
                raise ValueError("Invalid device type")

            if not set(chunk["sync_type"]).issubset(
                VALID_SYNC_TYPES
            ):
                raise ValueError("Invalid sync type")

            if (
                (chunk["duration_seconds"] < 0).any()
                or not chunk["is_late_event"].isin([0, 1]).all()
            ):
                raise ValueError("Invalid duration or late-event flag")

            # Enrollment relationships.
            enrolled_rows = chunk[
                chunk["enrollment_id"].notna()
            ]

            expected_learners = enrolled_rows[
                "enrollment_id"
            ].map(enrollment_learner)

            expected_courses = enrolled_rows[
                "enrollment_id"
            ].map(enrollment_course)

            if expected_learners.isna().any():
                raise ValueError("Unknown enrollment reference")

            if not (
                expected_learners.to_numpy()
                == enrolled_rows["learner_id"].to_numpy()
            ).all():
                raise ValueError("Enrollment learner mismatch")

            if not (
                expected_courses.to_numpy()
                == enrolled_rows["course_id"].to_numpy()
            ).all():
                raise ValueError("Enrollment course mismatch")

            # Content must belong to the event course.
            content_rows = chunk[
                chunk["content_item_id"].notna()
            ]

            expected_content_courses = (
                content_rows["content_item_id"]
                .map(content_course)
            )

            if expected_content_courses.isna().any():
                raise ValueError("Unknown content item reference")

            if not (
                expected_content_courses.to_numpy()
                == content_rows["course_id"].to_numpy()
            ).all():
                raise ValueError("Content/course relationship mismatch")

            # Unenrolled events must be labelled anomalies.
            unenrolled_rows = chunk[
                chunk["enrollment_id"].isna()
            ]

            for row in unenrolled_rows.itertuples(index=False):

                if truth_map.get(row.event_id) != "UNENROLLED_ACTIVITY":
                    raise ValueError(
                        "Unenrolled event missing ground-truth label"
                    )

                if (row.learner_id, row.course_id) in existing_pairs:
                    raise ValueError(
                        "Unenrolled anomaly has an existing enrollment pair"
                    )

                       # Timestamp checks
            chunk["event_time_utc"] = pd.to_datetime(
                chunk["event_time_utc"],
                format="mixed",
                errors="coerce",
            )

            chunk["received_at_utc"] = pd.to_datetime(
                chunk["received_at_utc"],
                format="mixed",
                errors="coerce",
            )

            if (
                chunk["event_time_utc"].isna().any()
                or chunk["received_at_utc"].isna().any()
            ):
                raise ValueError("Invalid event timestamp")

            if (
                chunk["received_at_utc"]
                < chunk["event_time_utc"]
            ).any():
                raise ValueError(
                    "Received timestamp precedes event timestamp"
                )
            # Enrollment date ordering.
            enrolled_times = enrolled_rows[
                "enrollment_id"
            ].map(enrollment_start)

            enrolled_event_times = chunk.loc[
                enrolled_rows.index, "event_time_utc"
            ]

            timezone_rows = chunk[
                chunk["event_id"].map(truth_map)
                == "TIMEZONE_MISALIGNMENT"
            ]

            ordinary_rows = chunk.drop(
                index=timezone_rows.index
            )

            ordinary_enrollment_rows = ordinary_rows[
                ordinary_rows["enrollment_id"].notna()
            ]

            ordinary_start_times = ordinary_enrollment_rows[
                "enrollment_id"
            ].map(enrollment_start)

            if (
                ordinary_enrollment_rows["event_time_utc"].to_numpy()
                < pd.to_datetime(ordinary_start_times).to_numpy()
            ).any():
                raise ValueError(
                    "Ordinary event occurs before enrollment"
                )

            # Withdrawn learners should not have later events.
            for row in ordinary_enrollment_rows.itertuples(index=False):

                if enrollment_status[row.enrollment_id] == "WITHDRAWN":

                    withdrawal_time = withdrawn_at[row.enrollment_id]

                    if (
                        pd.notna(withdrawal_time)
                        and row.event_time_utc > withdrawal_time
                    ):
                        raise ValueError(
                            "Event occurs after withdrawal"
                        )

            # Check labelled anomaly records.
            labelled = chunk[
                chunk["event_id"].isin(truth_map)
            ]

            for row in labelled.itertuples(index=False):

                issue = truth_map[row.event_id]

                issue_found[issue] += 1
                found_truth_ids.add(row.event_id)

                if issue == "DUPLICATE_EVENT":

                    expected_source = duplicate_expected[row.event_id]

                    if row.source_event_id != expected_source:
                        raise ValueError(
                            "Duplicate event source reference mismatch"
                        )

                elif issue == "PREMATURE_COMPLETION":

                    if row.event_type != "COURSE_COMPLETED":
                        raise ValueError(
                            "Premature completion has wrong event type"
                        )

                    first_attempt = earliest_attempt.get(
                        row.enrollment_id
                    )

                    if (
                        first_attempt is not None
                        and first_attempt <= row.event_time_utc
                    ):
                        raise ValueError(
                            "Premature completion has an earlier assessment attempt"
                        )

                elif issue == "TIMEZONE_MISALIGNMENT":

                    expected_time = pd.to_datetime(
                        timezone_expected[row.event_id]
                    )

                    if expected_time == row.event_time_utc:
                        raise ValueError(
                            "Timezone anomaly has no timestamp shift"
                        )

            total_rows += len(chunk)

            print(
                f"Validated {total_rows:,} / {EXPECTED_EVENTS:,} events"
            )

        connection.commit()

    finally:
        connection.close()

    # -------------------------------------------------
    # FINAL CHECKS
    # -------------------------------------------------

    if total_rows != EXPECTED_EVENTS:
        raise ValueError(
            f"Expected {EXPECTED_EVENTS:,} events, found {total_rows:,}"
        )

    if found_truth_ids != set(truth_map):
        raise ValueError(
            "Some ground-truth records do not have matching event rows"
        )

    for issue in VALID_ISSUES:
        if issue_found[issue] != 5_000:
            raise ValueError(
                f"Expected 5,000 event records for {issue}, "
                f"found {issue_found[issue]}"
            )

    print("\n" + "=" * 55)
    print("ACTIVITY EVENT VALIDATION PASSED")
    print("=" * 55)

    print(f"Total events: {total_rows:,}")
    print("Unique event IDs: PASSED")
    print("Learner and course references: PASSED")
    print("Enrollment relationships: PASSED")
    print("Content/course relationships: PASSED")
    print("Event and device types: PASSED")
    print("Timestamp ordering: PASSED")
    print("Ground-truth consistency: PASSED")

    print("\nAnomaly validation:")

    for issue, count in issue_found.items():
        print(f"{issue}: {count:,}")

    print("\nAll activity-event checks completed successfully.")

    # Remove temporary validation database.
    sqlite_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
