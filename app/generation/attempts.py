
from datetime import datetime, timedelta

import pandas as pd

from app.generation.config import (
    GenerationConfig,
    GENERATED_DIR,
    create_generators,
)


AS_OF_DATE = datetime(2026, 11, 12, 23, 59, 59)


def generate_attempts(rng):

    enrollments = pd.read_csv(
        GENERATED_DIR / "enrollments.csv"
    )

    assessments = pd.read_csv(
        GENERATED_DIR / "assessments.csv"
    )

    active_enrollments = enrollments[
        enrollments["enrollment_status"] == "IN_PROGRESS"
    ]

    published_assessments = assessments[
        assessments["assessment_status"] == "PUBLISHED"
    ]

    assessments_by_course = {
        course_id: group.to_dict("records")
        for course_id, group in published_assessments.groupby(
            "course_id"
        )
    }

    records = []

    attempt_statuses = [
        "GRADED",
        "SUBMITTED",
        "IN_PROGRESS",
        "ABANDONED",
    ]

    attempt_weights = [80, 10, 5, 5]

    for _, enrollment in active_enrollments.iterrows():

        course_assessments = assessments_by_course.get(
            enrollment["course_id"],
            [],
        )

        for assessment in course_assessments:

            # Not every learner attempts every assessment.
            if rng.random() > 0.70:
                continue

            enrollment_date = pd.to_datetime(
                enrollment["enrolled_at"]
            ).to_pydatetime()

            available_from = pd.to_datetime(
                assessment["available_from"]
            ).to_pydatetime()

            start_date = max(
                enrollment_date,
                available_from,
            )

            if start_date > AS_OF_DATE:
                continue

            maximum_attempts = rng.choices(
                [1, 2, 3],
                weights=[60, 28, 12],
                k=1,
            )[0]

            previous_start = None

            for attempt_number in range(
                1,
                maximum_attempts + 1,
            ):

                remaining_seconds = int(
                    (AS_OF_DATE - start_date).total_seconds()
                )

                if remaining_seconds < 1:
                    break

                earliest = (
                    previous_start
                    if previous_start is not None
                    else start_date
                )

                earliest = earliest + timedelta(minutes=5)

                if earliest > AS_OF_DATE:
                    break

                remaining_seconds = int(
                    (AS_OF_DATE - earliest).total_seconds()
                )

                started_at = earliest + timedelta(
                    seconds=rng.randint(
                        0,
                        remaining_seconds,
                    )
                )

                attempt_status = rng.choices(
                    attempt_statuses,
                    weights=attempt_weights,
                    k=1,
                )[0]

                submitted_at = None
                score = None
                is_passed = None

                if attempt_status in ["GRADED", "SUBMITTED"]:

                    submitted_at = started_at + timedelta(
                        minutes=rng.randint(5, 120)
                    )

                    if submitted_at > AS_OF_DATE:
                        submitted_at = AS_OF_DATE

                if attempt_status == "GRADED":

                    submitted_at = started_at + timedelta(
                        minutes=rng.randint(5, 120)
                    )

                    if submitted_at > AS_OF_DATE:
                        submitted_at = AS_OF_DATE

                    score = round(
                        rng.uniform(20, 100),
                        2,
                    )

                    is_passed = int(
                        score >= float(
                            assessment["passing_score"]
                        )
                    )

                records.append({
                    "assessment_id": assessment["assessment_id"],
                    "learner_id": enrollment["learner_id"],
                    "enrollment_id": enrollment["enrollment_id"],
                    "attempt_number": attempt_number,
                    "started_at": started_at,
                    "submitted_at": submitted_at,
                    "score": score,
                    "attempt_status": attempt_status,
                    "is_passed": is_passed,
                })

                previous_start = started_at

    return pd.DataFrame(records)


def validate_attempts(attempts):

    assessments = pd.read_csv(
        GENERATED_DIR / "assessments.csv"
    )

    enrollments = pd.read_csv(
        GENERATED_DIR / "enrollments.csv"
    )

    errors = []

    if attempts.empty:
        raise ValueError("No assessment attempts generated")

    if attempts.duplicated(
        subset=[
            "assessment_id",
            "enrollment_id",
            "attempt_number",
        ]
    ).any():
        errors.append("Duplicate assessment attempt numbers")

    if not attempts["assessment_id"].isin(
        assessments["assessment_id"]
    ).all():
        errors.append("Invalid assessment reference")

    if not attempts["enrollment_id"].isin(
        enrollments["enrollment_id"]
    ).all():
        errors.append("Invalid enrollment reference")

    if not attempts["learner_id"].isin(
        enrollments["learner_id"]
    ).all():
        errors.append("Invalid learner reference")

    if not attempts["attempt_status"].isin([
        "IN_PROGRESS",
        "SUBMITTED",
        "GRADED",
        "ABANDONED",
    ]).all():
        errors.append("Invalid attempt status")

    if (attempts["attempt_number"] > 3).any():
        errors.append("Attempt number exceeds maximum")

    graded = attempts[
        attempts["attempt_status"] == "GRADED"
    ]

    if graded["score"].isna().any():
        errors.append("Graded attempt missing score")

    if graded["is_passed"].isna().any():
        errors.append("Graded attempt missing pass result")

    ungraded = attempts[
        attempts["attempt_status"] != "GRADED"
    ]

    if ungraded["score"].notna().any():
        errors.append("Ungraded attempt contains score")

    if errors:
        raise ValueError("\n".join(errors))

    print("Assessment attempt validation: PASSED")
    print("Total attempts:", len(attempts))
    print("Unique enrollments:", attempts["enrollment_id"].nunique())


def main():

    config = GenerationConfig()

    rng, numpy_rng, fake = create_generators(
        config.seed + 3
    )

    print("Generating assessment attempts...")

    attempts = generate_attempts(rng)

    print("Validating assessment attempts...")

    validate_attempts(attempts)

    output_file = GENERATED_DIR / "attempts.csv"

    attempts.to_csv(
        output_file,
        index=False,
    )

    print("\nAssessment attempts generated successfully!")
    print("Records:", len(attempts))
    print("Saved:", output_file)

    print("\nAttempt status distribution:")
    print(attempts["attempt_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
