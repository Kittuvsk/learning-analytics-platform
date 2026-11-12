
from datetime import date, datetime, time, timedelta

import pandas as pd

from app.generation.config import (
    GenerationConfig,
    GENERATED_DIR,
    create_generators,
)


AS_OF_DATE = date(2026, 11, 12)


def random_datetime(rng, start_date, end_date):

    days = (end_date - start_date).days

    selected_date = start_date + timedelta(
        days=rng.randint(0, days)
    )

    seconds = rng.randint(0, 86399)

    return datetime.combine(
        selected_date,
        time.min,
    ) + timedelta(seconds=seconds)


def generate_enrollments(config, rng):

    learners = pd.read_csv(
        GENERATED_DIR / "learners.csv"
    )

    courses = pd.read_csv(
        GENERATED_DIR / "courses.csv"
    )

    cohorts = pd.read_csv(
        GENERATED_DIR / "cohorts.csv"
    )

    # Only active learners can receive new enrollments.
    eligible_learners = learners[
        learners["learner_status"] == "ACTIVE"
    ].copy()

    # Only published courses accept new enrollments.
    eligible_courses = courses[
        courses["course_status"] == "PUBLISHED"
    ].copy()

    if eligible_learners.empty or eligible_courses.empty:
        raise ValueError("No eligible learners or courses")

    eligible_learners["registration_date"] = pd.to_datetime(
        eligible_learners["registration_date"]
    ).dt.date

    eligible_courses["published_date"] = pd.to_datetime(
        eligible_courses["published_at"]
    ).dt.date

    cohorts["start_date"] = pd.to_datetime(
        cohorts["start_date"]
    ).dt.date

    cohorts["end_date"] = pd.to_datetime(
        cohorts["end_date"]
    ).dt.date

    learner_ids = eligible_learners["learner_id"].tolist()
    course_ids = eligible_courses["course_id"].tolist()

    learner_dates = dict(zip(
        eligible_learners["learner_id"],
        eligible_learners["registration_date"],
    ))

    course_dates = dict(zip(
        eligible_courses["course_id"],
        eligible_courses["published_date"],
    ))

    cohort_records = cohorts.to_dict("records")

    records = []
    used_pairs = set()

    statuses = [
    "ENROLLED",
    "IN_PROGRESS",
    "WITHDRAWN",
    "SUSPENDED",
     ]

    weights = [30, 55, 10, 5]
    print("Eligible learners:", len(learner_ids))
    print("Eligible courses:", len(course_ids))

    while len(records) < config.enrollment_count:

        learner_id = rng.choice(learner_ids)
        course_id = rng.choice(course_ids)

        pair = (learner_id, course_id)

        if pair in used_pairs:
            continue

        start_date = max(
            learner_dates[learner_id],
            course_dates[course_id],
        )

        if start_date > AS_OF_DATE:
            continue

        enrolled_at = random_datetime(
            rng,
            start_date,
            AS_OF_DATE,
        )

        available_days = (
            AS_OF_DATE - enrolled_at.date()
        ).days


        status = rng.choices(
            statuses,
            weights=weights,
            k=1,
        )[0]

        started_at = None
        completed_at = None
        withdrawn_at = None

        if status == "IN_PROGRESS":

            started_at = enrolled_at + timedelta(
                seconds=rng.randint(
                    1,
                    max(1, available_days * 86400),
                )
            )

        elif status == "WITHDRAWN":

            withdrawn_at = enrolled_at + timedelta(
                seconds=rng.randint(
                    1,
                    max(1, available_days * 86400),
                )
            )

        # Assign a cohort only when enrollment falls
        # inside that cohort's date range.
        matching_cohorts = [
            cohort
            for cohort in cohort_records
            if cohort["start_date"]
            <= enrolled_at.date()
            <= cohort["end_date"]
        ]

        cohort_id = None

        if matching_cohorts:
            cohort_id = rng.choice(
                matching_cohorts
            )["cohort_id"]

        enrollment_id = (
            f"ENR-{learner_id}-{course_id}"
        )

        records.append({
            "enrollment_id": enrollment_id,
            "learner_id": learner_id,
            "course_id": course_id,
            "cohort_id": cohort_id,
            "enrollment_status": status,
            "enrolled_at": enrolled_at,
            "started_at": started_at,
            "completed_at": completed_at,
            "withdrawn_at": withdrawn_at,
        })

        used_pairs.add(pair)

        if len(records) % 20000 == 0:
            print(
                f"Generated enrollments: {len(records)}"
            )

    return pd.DataFrame(records)


def validate_enrollments(enrollments, config):

    learners = pd.read_csv(
        GENERATED_DIR / "learners.csv"
    )

    courses = pd.read_csv(
        GENERATED_DIR / "courses.csv"
    )

    cohorts = pd.read_csv(
        GENERATED_DIR / "cohorts.csv"
    )

    errors = []

    if len(enrollments) != config.enrollment_count:
        errors.append("Enrollment count mismatch")

    if enrollments["enrollment_id"].duplicated().any():
        errors.append("Duplicate enrollment IDs")

    if enrollments.duplicated(
        subset=["learner_id", "course_id"]
    ).any():
        errors.append("Duplicate learner-course pairs")

    if not enrollments["learner_id"].isin(
        learners["learner_id"]
    ).all():
        errors.append("Invalid learner reference")

    if not enrollments["course_id"].isin(
        courses["course_id"]
    ).all():
        errors.append("Invalid course reference")

    if not enrollments["learner_id"].isin(
        learners.loc[
            learners["learner_status"] == "ACTIVE",
            "learner_id",
        ]
    ).all():
        errors.append("Inactive or suspended learner enrolled")

    if not enrollments["course_id"].isin(
        courses.loc[
            courses["course_status"] == "PUBLISHED",
            "course_id",
        ]
    ).all():
        errors.append("Unpublished course enrolled")

    if not enrollments["cohort_id"].dropna().isin(
        cohorts["cohort_id"]
    ).all():
        errors.append("Invalid cohort reference")

    valid_statuses = [
        "ENROLLED",
        "IN_PROGRESS",
        "COMPLETED",
        "WITHDRAWN",
        "SUSPENDED",
    ]

    if not enrollments["enrollment_status"].isin(
        valid_statuses
    ).all():
        errors.append("Invalid enrollment status")

    enrollments["enrolled_at"] = pd.to_datetime(
        enrollments["enrolled_at"]
    )

    for column in [
        "started_at",
        "completed_at",
        "withdrawn_at",
    ]:
        enrollments[column] = pd.to_datetime(
            enrollments[column]
        )

    if (
        enrollments["started_at"].notna()
        & (
            enrollments["started_at"]
            < enrollments["enrolled_at"]
        )
    ).any():
        errors.append("Start date before enrollment")

    if (
        enrollments["completed_at"].notna()
        & (
            enrollments["completed_at"]
            < enrollments["started_at"]
        )
    ).any():
        errors.append("Completion date before start date")

    if (
        enrollments["withdrawn_at"].notna()
        & (
            enrollments["withdrawn_at"]
            < enrollments["enrolled_at"]
        )
    ).any():
        errors.append("Withdrawal date before enrollment")

    completed = enrollments[
        enrollments["enrollment_status"] == "COMPLETED"
    ]

    if completed["completed_at"].isna().any():
        errors.append("Completed enrollment missing completion date")

    in_progress = enrollments[
        enrollments["enrollment_status"] == "IN_PROGRESS"
    ]

    if in_progress["started_at"].isna().any():
        errors.append("In-progress enrollment missing start date")

    withdrawn = enrollments[
        enrollments["enrollment_status"] == "WITHDRAWN"
    ]

    if withdrawn["withdrawn_at"].isna().any():
        errors.append("Withdrawn enrollment missing withdrawal date")

    if errors:
        raise ValueError("\n".join(errors))

    print("Enrollment validation: PASSED")
    print("Unique enrollment IDs:", enrollments["enrollment_id"].nunique())
    print("Unique learner-course pairs:", len(enrollments))
    print("Valid learner references: PASSED")
    print("Valid course references: PASSED")
    print("Valid cohort references: PASSED")
    print("Lifecycle date checks: PASSED")


def main():

    config = GenerationConfig()

    rng, numpy_rng, fake = create_generators(
        config.seed + 2
    )

    print("Starting enrollment generation...")

    enrollments = generate_enrollments(
        config,
        rng,
    )

    print("\nValidating enrollment records...")

    validate_enrollments(
        enrollments,
        config,
    )

    output_file = GENERATED_DIR / "enrollments.csv"

    enrollments.to_csv(
        output_file,
        index=False,
    )

    print("\nEnrollment generation completed!")
    print("Total enrollments:", len(enrollments))
    print("Saved:", output_file)

    print("\nEnrollment status distribution:")
    print(
        enrollments["enrollment_status"]
        .value_counts()
        .to_string()
    )


if __name__ == "__main__":
    main()
