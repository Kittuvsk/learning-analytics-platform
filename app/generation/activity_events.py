
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.generation.config import (
    GenerationConfig,
    RANDOM_SEED,
    GENERATED_DIR,
    GROUND_TRUTH_DIR,
    MANIFEST_DIR,
    create_data_directories,
    create_generators,
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

config = GenerationConfig()

TOTAL_EVENTS = config.activity_event_count
ANOMALIES_PER_TYPE = 5_000
TOTAL_ANOMALIES = ANOMALIES_PER_TYPE * 4
BASELINE_EVENTS = TOTAL_EVENTS - TOTAL_ANOMALIES
BATCH_SIZE = 50_000

AS_OF_DATE = pd.Timestamp("2026-11-12 23:59:59")

EVENT_FILE = GENERATED_DIR / "activity_events.csv"
GROUND_TRUTH_FILE = GROUND_TRUTH_DIR / "ground_truth.csv"
MANIFEST_FILE = MANIFEST_DIR / "activity_events_manifest.json"

SEED = RANDOM_SEED + 4


EVENT_TYPES = [
    "LOGIN",
    "COURSE_OPENED",
    "CONTENT_VIEWED",
    "VIDEO_PLAYED",
    "VIDEO_COMPLETED",
    "DOCUMENT_DOWNLOADED",
    "QUIZ_STARTED",
    "QUIZ_SUBMITTED",
    "ASSIGNMENT_SUBMITTED",
    "OTHER",
]

EVENT_WEIGHTS = [
    5, 15, 25, 15, 12, 8, 8, 6, 4, 2
]

DEVICE_TYPES = ["DESKTOP", "MOBILE", "TABLET", "OTHER"]
DEVICE_WEIGHTS = [30, 45, 15, 10]

TIMEZONES = [
    "Asia/Kolkata",
    "UTC",
    "Europe/London",
    "Asia/Dubai",
    "America/New_York",
    "Asia/Singapore",
]

EVENT_COLUMNS = [
    "event_id",
    "learner_id",
    "course_id",
    "enrollment_id",
    "content_item_id",
    "event_type",
    "event_time_utc",
    "received_at_utc",
    "learner_timezone",
    "device_type",
    "sync_type",
    "duration_seconds",
    "source_event_id",
    "is_late_event",
]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def load_sources():

    print("Loading source CSV files...")

    learners = pd.read_csv(
        GENERATED_DIR / "learners.csv"
    )

    courses = pd.read_csv(
        GENERATED_DIR / "courses.csv"
    )

    enrollments = pd.read_csv(
        GENERATED_DIR / "enrollments.csv"
    )

    content = pd.read_csv(
        GENERATED_DIR / "content_items.csv"
    )

    attempts = pd.read_csv(
        GENERATED_DIR / "attempts.csv"
    )

    for column in ["enrolled_at", "withdrawn_at"]:
        enrollments[column] = pd.to_datetime(
            enrollments[column],
            errors="coerce",
        )

    learners["registration_date"] = pd.to_datetime(
        learners["registration_date"],
        errors="coerce",
    )

    attempts["started_at"] = pd.to_datetime(
        attempts["started_at"],
        errors="coerce",
    )

    print("Source files loaded successfully.")

    return learners, courses, enrollments, content, attempts


def build_content_map(content):

    result = {}

    for course_id, group in content.groupby("course_id"):
        ids = group["content_item_id"].dropna().astype("int64").to_numpy()

        if len(ids):
            result[course_id] = ids

    return result


def make_event_id(enrollment_id, sequence):

    if pd.isna(enrollment_id) or enrollment_id is None:
        return f"EVT-UNENROLLED-{sequence:09d}"

    return f"EVT-{enrollment_id}-{sequence:09d}"


def calculate_checksum(path):

    sha256 = hashlib.sha256()

    with open(path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# ---------------------------------------------------------
# BASELINE EVENT GENERATOR
# ---------------------------------------------------------

def generate_baseline_batch(
    enrollments,
    learner_timezone_map,
    content_map,
    rng,
    sequence_start,
    batch_size,
):

    selected_positions = rng.integers(
        0,
        len(enrollments),
        size=batch_size,
    )

    batch = enrollments.iloc[selected_positions].reset_index(
        drop=True
    )

    learner_ids = batch["learner_id"].to_numpy()
    course_ids = batch["course_id"].to_numpy()
    enrollment_ids = batch["enrollment_id"].to_numpy()

    # Learner timezones.
    timezones = np.array([
        learner_timezone_map.get(learner_id, "UTC")
        for learner_id in learner_ids
    ])

    # Choose content belonging to the correct course.
    content_ids = np.empty(batch_size, dtype=object)
    content_ids[:] = None

    for course_id in pd.unique(course_ids):

        positions = np.flatnonzero(course_ids == course_id)

        available = content_map.get(course_id)

        if available is not None:
            content_ids[positions] = rng.choice(
                available,
                size=len(positions),
            )

    # Random event types.
    event_types = rng.choice(
        EVENT_TYPES,
        size=batch_size,
        p=np.array(EVENT_WEIGHTS) / sum(EVENT_WEIGHTS),
    )

    # LOGIN and COURSE_OPENED do not require content.
    no_content = np.isin(
        event_types,
        ["LOGIN", "COURSE_OPENED"],
    )

    content_ids[no_content] = None


    # Generate event timestamps.
    # Normalize both datetime columns to nanoseconds
    # before converting them to integer timestamps.

    enrolled_ns = (
        batch["enrolled_at"]
        .astype("datetime64[ns]")
        .astype("int64")
        .to_numpy()
    )

    upper_dates = pd.Series(
        pd.Timestamp(AS_OF_DATE),
        index=batch.index,
        dtype="datetime64[ns]",
    )

    withdrawn = batch["enrollment_status"].eq("WITHDRAWN")

    upper_dates.loc[withdrawn] = batch.loc[
        withdrawn,
        "withdrawn_at",
    ]

    upper_ns = (
        upper_dates
        .astype("datetime64[ns]")
        .astype("int64")
        .to_numpy()
    )

    upper_ns = np.maximum(upper_ns, enrolled_ns)

    fractions = rng.random(batch_size)

    event_ns = (
        enrolled_ns
        + ((upper_ns - enrolled_ns) * fractions).astype("int64")
    )

    # Explicitly interpret integer timestamps as nanoseconds.
    event_times = pd.to_datetime(
        event_ns,
        unit="ns",
    )

    # ONLINE and OFFLINE_SYNC.
    offline = rng.random(batch_size) < 0.20

    sync_types = np.where(
        offline,
        "OFFLINE_SYNC",
        "ONLINE",
    )

    online_delays = rng.integers(
        0,
        31,
        size=batch_size,
    )

    offline_delays = rng.integers(
        1,
        168,
        size=batch_size,
    )

    delay_hours = np.where(
        offline,
        offline_delays,
        0,
    )

    delay_minutes = np.where(
        offline,
        0,
        online_delays,
    )

    received_times = (
        event_times
        + pd.to_timedelta(delay_hours, unit="h")
        + pd.to_timedelta(delay_minutes, unit="m")
    )

    delay_seconds = (
        received_times - event_times
    ).total_seconds()

    is_late = (delay_seconds > 86400).astype(int)

    # Device selection.
    devices = rng.choice(
        DEVICE_TYPES,
        size=batch_size,
        p=np.array(DEVICE_WEIGHTS) / sum(DEVICE_WEIGHTS),
    )

    durations = rng.integers(
        10,
        3601,
        size=batch_size,
    )

    durations[np.isin(
        event_types,
        ["LOGIN", "COURSE_OPENED"],
    )] = 0

    event_ids = [
        make_event_id(enrollment_id, sequence_start + i)
        for i, enrollment_id in enumerate(enrollment_ids)
    ]

    source_ids = [
        f"SRC-{event_id}" if offline[i] else None
        for i, event_id in enumerate(event_ids)
    ]

    result = pd.DataFrame({
        "event_id": event_ids,
        "learner_id": learner_ids,
        "course_id": course_ids,
        "enrollment_id": enrollment_ids,
        "content_item_id": content_ids,
        "event_type": event_types,
        "event_time_utc": event_times,
        "received_at_utc": received_times,
        "learner_timezone": timezones,
        "device_type": devices,
        "sync_type": sync_types,
        "duration_seconds": durations,
        "source_event_id": source_ids,
        "is_late_event": is_late,
    })

    return result[EVENT_COLUMNS]


# ---------------------------------------------------------
# SPECIAL EVENT HELPER
# ---------------------------------------------------------

def make_special_event(
    learner_id,
    course_id,
    enrollment_id,
    content_item_id,
    event_type,
    event_time,
    learner_timezone,
    sequence,
    rng,
    source_event_id=None,
):

    offline = rng.random() < 0.20

    if offline:
        delay_seconds = int(rng.integers(3600, 604801))
        sync_type = "OFFLINE_SYNC"
    else:
        delay_seconds = int(rng.integers(0, 1801))
        sync_type = "ONLINE"

    received_at = (
        event_time
        + pd.Timedelta(seconds=delay_seconds)
    )

    return {
        "event_id": make_event_id(
            enrollment_id,
            sequence,
        ),
        "learner_id": learner_id,
        "course_id": course_id,
        "enrollment_id": enrollment_id,
        "content_item_id": content_item_id,
        "event_type": event_type,
        "event_time_utc": event_time,
        "received_at_utc": received_at,
        "learner_timezone": learner_timezone,
        "device_type": rng.choice(DEVICE_TYPES),
        "sync_type": sync_type,
        "duration_seconds": int(rng.integers(0, 3601)),
        "source_event_id": source_event_id,
        "is_late_event": int(delay_seconds > 86400),
    }


# ---------------------------------------------------------
# ANOMALY GENERATION
# ---------------------------------------------------------

def generate_anomalies(
    learners,
    courses,
    enrollments,
    content,
    attempts,
    candidate_pool,
    learner_timezone_map,
    content_map,
    rng,
):

    print("\nGenerating controlled anomalies...")

    anomalies = []
    ground_truth = []

    sequence = BASELINE_EVENTS + 1

    # -----------------------------------------------
    # 1. DUPLICATE EVENTS
    # -----------------------------------------------

    print("Generating duplicate events...")

    duplicate_sources = candidate_pool.sample(
        n=ANOMALIES_PER_TYPE,
        random_state=SEED,
        replace=False,
    )

    for _, original in duplicate_sources.iterrows():

        original_event_id = original["event_id"]

        duplicate = original.copy()

        duplicate["event_id"] = make_event_id(
            original["enrollment_id"],
            sequence,
        )

        duplicate["source_event_id"] = original_event_id

        duplicate["received_at_utc"] = (
            pd.to_datetime(original["received_at_utc"])
            + pd.Timedelta(seconds=1)
        )

        anomalies.append(duplicate.to_dict())

        ground_truth.append({
            "issue_type": "DUPLICATE_EVENT",
            "entity_type": "ACTIVITY_EVENT",
            "entity_id": duplicate["event_id"],
            "expected_label": 1,
            "expected_value": original_event_id,
            "explanation": (
                "Duplicate of an existing activity event. "
                "The source_event_id identifies the original."
            ),
            "generator_seed": SEED,
        })

        sequence += 1

    # -----------------------------------------------
    # 2. UNENROLLED LEARNER ACTIVITY
    # -----------------------------------------------

    print("Generating unenrolled activity...")

    existing_pairs = set(
        zip(
            enrollments["learner_id"],
            enrollments["course_id"],
        )
    )

    learner_ids = learners["learner_id"].to_numpy()

    published_courses = courses.loc[
        courses["course_status"] == "PUBLISHED",
        "course_id",
    ].to_numpy()

    unenrolled_pairs = set()

    while len(unenrolled_pairs) < ANOMALIES_PER_TYPE:

        learner_id = rng.choice(learner_ids)
        course_id = rng.choice(published_courses)

        pair = (learner_id, course_id)

        if pair in existing_pairs or pair in unenrolled_pairs:
            continue

        unenrolled_pairs.add(pair)

    learner_lookup = learners.set_index("learner_id")

    for learner_id, course_id in sorted(unenrolled_pairs):

        learner = learner_lookup.loc[learner_id]

        registration = learner["registration_date"]

        lower = max(
            registration,
            pd.Timestamp("2025-01-01"),
        )

        if lower > AS_OF_DATE:
            lower = AS_OF_DATE

        seconds = int(
            rng.integers(
                0,
                max(1, int((AS_OF_DATE - lower).total_seconds()) + 1),
            )
        )

        event_time = lower + pd.Timedelta(seconds=seconds)

        available_content = content_map[course_id]

        content_id = int(rng.choice(available_content))

        timezone_name = learner["timezone"]

        event = make_special_event(
            learner_id=learner_id,
            course_id=course_id,
            enrollment_id=None,
            content_item_id=content_id,
            event_type="CONTENT_VIEWED",
            event_time=event_time,
            learner_timezone=timezone_name,
            sequence=sequence,
            rng=rng,
        )

        anomalies.append(event)

        ground_truth.append({
            "issue_type": "UNENROLLED_ACTIVITY",
            "entity_type": "ACTIVITY_EVENT",
            "entity_id": event["event_id"],
            "expected_label": 1,
            "expected_value": "NO_ENROLLMENT",
            "explanation": (
                "Learner generated activity for a course "
                "without a matching enrollment."
            ),
            "generator_seed": SEED,
        })

        sequence += 1

    # -----------------------------------------------
    # 3. PREMATURE COURSE COMPLETION
    # -----------------------------------------------

    print("Generating premature completion events...")

    earliest_attempt = (
        attempts.groupby("enrollment_id")["started_at"]
        .min()
    )

    candidates = enrollments[
        enrollments["enrollment_status"] == "IN_PROGRESS"
    ].copy()

    candidates["first_attempt"] = (
        candidates["enrollment_id"]
        .map(earliest_attempt)
    )

    candidates["completion_time"] = (
        candidates["enrolled_at"]
        + pd.Timedelta(seconds=1)
    )

    candidates = candidates[
        candidates["first_attempt"].isna()
        | (
            candidates["first_attempt"]
            > candidates["completion_time"]
        )
    ]

    if len(candidates) < ANOMALIES_PER_TYPE:
        raise ValueError(
            "Not enough valid enrollments for premature completion anomalies."
        )

    selected = candidates.sample(
        n=ANOMALIES_PER_TYPE,
        random_state=SEED + 1,
    )

    for _, enrollment in selected.iterrows():

        learner_id = enrollment["learner_id"]
        course_id = enrollment["course_id"]
        enrollment_id = enrollment["enrollment_id"]

        event_time = (
            enrollment["enrolled_at"]
            + pd.Timedelta(seconds=1)
        )

        timezone_name = learner_timezone_map.get(
            learner_id,
            "UTC",
        )

        event = make_special_event(
            learner_id=learner_id,
            course_id=course_id,
            enrollment_id=enrollment_id,
            content_item_id=None,
            event_type="COURSE_COMPLETED",
            event_time=event_time,
            learner_timezone=timezone_name,
            sequence=sequence,
            rng=rng,
        )

        anomalies.append(event)

        ground_truth.append({
            "issue_type": "PREMATURE_COMPLETION",
            "entity_type": "ACTIVITY_EVENT",
            "entity_id": event["event_id"],
            "expected_label": 1,
            "expected_value": "REQUIRED_ASSESSMENTS_NOT_COMPLETED",
            "explanation": (
                "Course completion was recorded before any "
                "assessment attempt for this enrollment."
            ),
            "generator_seed": SEED,
        })

        sequence += 1

    # -----------------------------------------------
    # 4. TIMEZONE MISALIGNMENT
    # -----------------------------------------------


    # -----------------------------------------------
    # 4. TIMEZONE MISALIGNMENT
    # -----------------------------------------------

    print("Generating timezone misalignment events...")

    # Select learners with non-zero UTC offsets.
    nonzero_timezones = {
        "Asia/Dubai",
        "America/New_York",
        "Asia/Singapore",
        "Asia/Kolkata",
    }

    eligible_timezone_learners = {
        learner_id
        for learner_id, timezone_name in learner_timezone_map.items()
        if timezone_name in nonzero_timezones
    }

    timezone_candidates = enrollments[
        (enrollments["enrollment_status"] == "IN_PROGRESS")
        & (enrollments["learner_id"].isin(eligible_timezone_learners))
        & (enrollments["enrolled_at"].notna())
        & (
            enrollments["enrolled_at"]
            <= AS_OF_DATE - pd.Timedelta(days=2)
        )
    ]
    if len(timezone_candidates) < ANOMALIES_PER_TYPE:
        raise ValueError(
            "Not enough eligible enrollments for timezone anomalies"
        )

    timezone_enrollments = timezone_candidates.sample(
        n=ANOMALIES_PER_TYPE,
        random_state=SEED + 2,
        replace=False,
    )

    # Generate timezone anomaly events.
    for _, enrollment in timezone_enrollments.iterrows():

        learner_id = enrollment["learner_id"]
        course_id = enrollment["course_id"]
        enrollment_id = enrollment["enrollment_id"]

        timezone_name = learner_timezone_map[learner_id]

        # Generate a correct UTC timestamp at least two days
        # after enrollment.
        lower = enrollment["enrolled_at"] + pd.Timedelta(days=2)

        seconds = int(
            rng.integers(
                0,
                max(1, int((AS_OF_DATE - lower).total_seconds()) + 1),
            )
        )

        correct_utc = (
            lower + pd.Timedelta(seconds=seconds)
        ).to_pydatetime().replace(tzinfo=timezone.utc)

        # Intentionally store local wall-clock time as UTC.
        local_wall_time = (
            correct_utc
            .astimezone(ZoneInfo(timezone_name))
            .replace(tzinfo=None)
        )

        wrong_event_time = pd.Timestamp(local_wall_time)

        content_id = int(
            rng.choice(content_map[course_id])
        )

        event = make_special_event(
            learner_id=learner_id,
            course_id=course_id,
            enrollment_id=enrollment_id,
            content_item_id=content_id,
            event_type="CONTENT_VIEWED",
            event_time=wrong_event_time,
            learner_timezone=timezone_name,
            sequence=sequence,
            rng=rng,
        )

        anomalies.append(event)

        ground_truth.append({
            "issue_type": "TIMEZONE_MISALIGNMENT",
            "entity_type": "ACTIVITY_EVENT",
            "entity_id": event["event_id"],
            "expected_label": 1,
            "expected_value": (
                correct_utc.replace(tzinfo=None).isoformat()
            ),
            "explanation": (
                "Local wall-clock time was incorrectly stored "
                "as UTC instead of converting it to UTC."
            ),
            "generator_seed": SEED,
        })

        sequence += 1
        anomaly_df = pd.DataFrame(
        anomalies,
        columns=EVENT_COLUMNS,
    )

    ground_truth_df = pd.DataFrame(ground_truth)

    print("Anomaly generation completed.")

    return anomaly_df, ground_truth_df

# ---------------------------------------------------------
# MAIN GENERATION
# ---------------------------------------------------------

def main():

    create_data_directories()

    rng = np.random.default_rng(SEED)

    (
        learners,
        courses,
        enrollments,
        content,
        attempts,
    ) = load_sources()

    if len(enrollments) == 0 or len(learners) == 0:
        raise ValueError("Required source data is empty.")

    content_map = build_content_map(content)

    learner_timezone_map = (
        learners.set_index("learner_id")["timezone"].to_dict()
    )

    # Only enrollments with valid content are used.
    enrollments = enrollments[
        enrollments["course_id"].isin(content_map)
    ].copy()

    enrollments = enrollments[
        enrollments["enrolled_at"].notna()
    ].copy()

    if enrollments.empty:
        raise ValueError("No valid enrollments available.")

    # Reset previous output so repeated runs do not append
    # to an older generation.
    if EVENT_FILE.exists():
        EVENT_FILE.unlink()

    if GROUND_TRUTH_FILE.exists():
        GROUND_TRUTH_FILE.unlink()

    if MANIFEST_FILE.exists():
        MANIFEST_FILE.unlink()

    print("\nStarting baseline event generation...")
    print("Target baseline records:", BASELINE_EVENTS)
    print("Batch size:", BATCH_SIZE)

    candidate_pool = None
    records_written = 0

    while records_written < BASELINE_EVENTS:

        current_batch_size = min(
            BATCH_SIZE,
            BASELINE_EVENTS - records_written,
        )

        batch = generate_baseline_batch(
            enrollments=enrollments,
            learner_timezone_map=learner_timezone_map,
            content_map=content_map,
            rng=rng,
            sequence_start=records_written + 1,
            batch_size=current_batch_size,
        )

        batch.to_csv(
            EVENT_FILE,
            mode="a",
            header=not EVENT_FILE.exists(),
            index=False,
        )

        if candidate_pool is None:
            candidate_pool = batch.head(
                ANOMALIES_PER_TYPE
            ).copy()

        records_written += len(batch)

        print(
            f"Baseline events generated: "
            f"{records_written:,}/{BASELINE_EVENTS:,}"
        )

        del batch

    print("\nBaseline generation completed.")

    anomaly_df, ground_truth_df = generate_anomalies(
        learners=learners,
        courses=courses,
        enrollments=enrollments,
        content=content,
        attempts=attempts,
        candidate_pool=candidate_pool,
        learner_timezone_map=learner_timezone_map,
        content_map=content_map,
        rng=rng,
    )

    print("\nAppending anomaly events...")

    anomaly_df.to_csv(
        EVENT_FILE,
        mode="a",
        header=False,
        index=False,
    )

    ground_truth_df.to_csv(
        GROUND_TRUTH_FILE,
        index=False,
    )

    # -----------------------------------------------------
    # FINAL COUNTS
    # -----------------------------------------------------

    final_count = records_written + len(anomaly_df)

    if final_count != TOTAL_EVENTS:
        raise ValueError(
            f"Expected {TOTAL_EVENTS:,} events, got {final_count:,}"
        )

    if anomaly_df["event_id"].duplicated().any():
        raise ValueError("Duplicate anomaly event IDs detected.")

    if ground_truth_df["entity_id"].duplicated().any():
        raise ValueError("Duplicate ground truth entity IDs detected.")

    if set(anomaly_df["event_id"]) != set(
        ground_truth_df["entity_id"]
    ):
        raise ValueError(
            "Anomaly events and ground truth records do not match."
        )

    # -----------------------------------------------------
    # MANIFEST
    # -----------------------------------------------------

    manifest = {
        "dataset": "learning_analytics_activity_events",
        "master_seed": RANDOM_SEED,

        "generator_seed": SEED,
        "total_records": final_count,
        "baseline_records": records_written,
        "anomaly_records": len(anomaly_df),
        "anomalies_per_type": ANOMALIES_PER_TYPE,
        "batch_size": BATCH_SIZE,
        "event_file": str(EVENT_FILE),
        "ground_truth_file": str(GROUND_TRUTH_FILE),
        "sha256": calculate_checksum(EVENT_FILE),
        "ground_truth_sha256": calculate_checksum(
            GROUND_TRUTH_FILE
        ),
        "anomaly_distribution": (
            ground_truth_df["issue_type"]
            .value_counts()
            .to_dict()
        ),
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    print("\n" + "=" * 55)
    print("ACTIVITY EVENT GENERATION COMPLETED")
    print("=" * 55)

    print(f"Total events: {final_count:,}")
    print(f"Baseline events: {records_written:,}")
    print(f"Anomaly events: {len(anomaly_df):,}")

    print("\nAnomaly distribution:")
    print(ground_truth_df["issue_type"].value_counts())

    print("\nSaved files:")
    print(EVENT_FILE)
    print(GROUND_TRUTH_FILE)
    print(MANIFEST_FILE)

    print("\nSHA256:", manifest["sha256"])


if __name__ == "__main__":
    main()
