
import pandas as pd

from app.generation.config import GENERATED_DIR


def main():

    attempts = pd.read_csv(GENERATED_DIR / "attempts.csv")
    enrollments = pd.read_csv(GENERATED_DIR / "enrollments.csv")
    assessments = pd.read_csv(GENERATED_DIR / "assessments.csv")

    errors = []

    # Join attempts to their actual enrollment.
    data = attempts.merge(
        enrollments[
            [
                "enrollment_id",
                "learner_id",
                "course_id",
                "enrollment_status",
                "enrolled_at",
            ]
        ],
        on="enrollment_id",
        how="left",
        suffixes=("", "_enrollment"),
        validate="many_to_one",
    )

    if data["course_id"].isna().any():
        errors.append("Attempt has invalid enrollment")

    if (
        data["learner_id"]
        != data["learner_id_enrollment"]
    ).any():
        errors.append("Attempt learner does not match enrollment")

    if not (
        data["enrollment_status"] == "IN_PROGRESS"
    ).all():
        errors.append("Attempt belongs to non-active enrollment")

    # Join to the assessment.
    data = data.merge(
        assessments[
            [
                "assessment_id",
                "course_id",
                "available_from",
                "assessment_status",
                "maximum_score",
                "passing_score",
            ]
        ],
        on="assessment_id",
        how="left",
        suffixes=("_enrollment", "_assessment"),
        validate="many_to_one",
    )

    if data["course_id_assessment"].isna().any():
        errors.append("Missing assessment course reference")

    if (
        data["course_id_enrollment"]
        != data["course_id_assessment"]
    ).any():
        errors.append("Assessment does not belong to enrollment course")

    if not (
        data["assessment_status"] == "PUBLISHED"
    ).all():
        errors.append("Attempt references unpublished assessment")

    # Convert timestamps.
    for column in [
        "started_at",
        "submitted_at",
        "enrolled_at",
        "available_from",
    ]:
        data[column] = pd.to_datetime(
            data[column],
            errors="coerce",
        )

    minimum_start = data[
        ["enrolled_at", "available_from"]
    ].max(axis=1)

    if (data["started_at"] < minimum_start).any():
        errors.append("Attempt starts before enrollment or availability")

    submitted = data[
        data["attempt_status"].isin(["SUBMITTED", "GRADED"])
    ]

    if submitted["submitted_at"].isna().any():
        errors.append("Submitted attempt missing timestamp")

    if (
        submitted["submitted_at"]
        < submitted["started_at"]
    ).any():
        errors.append("Submission occurs before attempt start")

    # Score and pass/fail consistency.
    graded = data[data["attempt_status"] == "GRADED"]

    if graded["score"].isna().any():
        errors.append("Graded attempt missing score")

    if (
        (graded["score"] < 0)
        | (graded["score"] > graded["maximum_score"])
    ).any():
        errors.append("Score outside permitted range")

    expected_pass = (
        graded["score"] >= graded["passing_score"]
    ).astype(int)

    if not (graded["is_passed"] == expected_pass).all():
        errors.append("Incorrect pass/fail calculation")

    ungraded = data[
        data["attempt_status"] != "GRADED"
    ]

    if ungraded["score"].notna().any():
        errors.append("Ungraded attempt contains score")

    if ungraded["is_passed"].notna().any():
        errors.append("Ungraded attempt contains pass/fail result")

    # Maximum attempts and unique sequence.
    grouped = data.groupby(
        ["enrollment_id", "assessment_id"]
    )["attempt_number"]

    if (grouped.max() > 3).any():
        errors.append("More than three attempts found")

    if data.duplicated(
        ["enrollment_id", "assessment_id", "attempt_number"]
    ).any():
        errors.append("Duplicate attempt sequence")

    if errors:
        print("\nATTEMPT VALIDATION FAILED")

        for error in errors:
            print("-", error)

        raise SystemExit(1)

    print("\nALL DEEP ASSESSMENT VALIDATIONS PASSED!")
    print("Valid enrollment relationships: PASSED")
    print("Valid assessment relationships: PASSED")
    print("Valid timestamps: PASSED")
    print("Score and pass/fail consistency: PASSED")
    print("Maximum attempt limit: PASSED")


if __name__ == "__main__":
    main()
