
import pandas as pd

from app.generation.config import (
    GenerationConfig,
    create_generators,
    create_data_directories,
    GENERATED_DIR,
)


def generate_learners(config, rng, fake):

    learners = []

    statuses = ["ACTIVE", "INACTIVE", "SUSPENDED"]
    status_weights = [0.82, 0.12, 0.06]

    timezones = [
        "Asia/Kolkata",
        "Asia/Dubai",
        "Europe/London",
        "America/New_York",
        "Asia/Singapore",
        "UTC",
    ]

    for i in range(1, config.learner_count + 1):

        learner = {
            "learner_id": f"LRN-{i:06d}",
            "user_id": None,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"learner{i:06d}@example.com",
            "learner_status": rng.choices(
                statuses,
                weights=status_weights,
                k=1,
            )[0],
            "registration_date": fake.date_between(
                start_date="-3y",
                end_date="today",
            ).isoformat(),
            "timezone": rng.choice(timezones),
        }

        learners.append(learner)

    return pd.DataFrame(learners)


def generate_courses(config, rng, fake):

    courses = []

    categories = [
        "Programming",
        "Data Science",
        "Artificial Intelligence",
        "Cloud Computing",
        "Database Management",
        "Cybersecurity",
        "Business Analytics",
        "Software Engineering",
        "DevOps",
        "Mathematics",
    ]

    difficulties = [
        "BEGINNER",
        "INTERMEDIATE",
        "ADVANCED",
    ]

    statuses = [
        "DRAFT",
        "PUBLISHED",
        "ARCHIVED",
    ]

    for i in range(1, config.course_count + 1):

        status = rng.choices(
            statuses,
            weights=[0.10, 0.82, 0.08],
            k=1,
        )[0]

        published_at = None

        if status == "PUBLISHED":
            published_at = fake.date_time_between(
                start_date="-3y",
                end_date="now",
            ).strftime("%Y-%m-%d %H:%M:%S")

        course = {
            "course_id": f"CRS-{i:06d}",
            "course_name": f"{rng.choice(categories)} - {fake.catch_phrase()}",
            "description": fake.text(max_nb_chars=180),
            "category": rng.choice(categories),
            "difficulty_level": rng.choice(difficulties),
            "course_status": status,
            "duration_hours": round(
                rng.uniform(2, 80),
                2,
            ),
            "published_at": published_at,
        }

        courses.append(course)

    return pd.DataFrame(courses)


def validate_master_data(learners, courses, config):

    errors = []

    # Learner checks
    if len(learners) != config.learner_count:
        errors.append("Learner row count mismatch")

    if learners["learner_id"].duplicated().any():
        errors.append("Duplicate learner IDs found")

    if learners["email"].duplicated().any():
        errors.append("Duplicate learner emails found")

    if not learners["learner_id"].str.match(
        r"^LRN-\d{6}$"
    ).all():
        errors.append("Invalid learner ID format")

    if not learners["learner_status"].isin(
        ["ACTIVE", "INACTIVE", "SUSPENDED", "COMPLETED"]
    ).all():
        errors.append("Invalid learner status")

    # Course checks
    if len(courses) != config.course_count:
        errors.append("Course row count mismatch")

    if courses["course_id"].duplicated().any():
        errors.append("Duplicate course IDs found")

    if not courses["course_id"].str.match(
        r"^CRS-\d{6}$"
    ).all():
        errors.append("Invalid course ID format")

    if not courses["difficulty_level"].isin(
        ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
    ).all():
        errors.append("Invalid course difficulty")

    if not courses["course_status"].isin(
        ["DRAFT", "PUBLISHED", "ARCHIVED"]
    ).all():
        errors.append("Invalid course status")

    if (courses["duration_hours"] <= 0).any():
        errors.append("Invalid course duration")

    if errors:
        raise ValueError("\n".join(errors))

    print("Master data validation: PASSED")
    print(f"Unique learners: {learners['learner_id'].nunique()}")
    print(f"Unique courses: {courses['course_id'].nunique()}")


def main():

    config = GenerationConfig()

    create_data_directories()

    rng, numpy_rng, fake = create_generators(config.seed)

    print("Generating learners...")

    learners = generate_learners(
        config,
        rng,
        fake,
    )

    print("Generating courses...")

    courses = generate_courses(
        config,
        rng,
        fake,
    )

    print("Validating master data...")

    validate_master_data(
        learners,
        courses,
        config,
    )

    learners.to_csv(
        GENERATED_DIR / "learners.csv",
        index=False,
    )

    courses.to_csv(
        GENERATED_DIR / "courses.csv",
        index=False,
    )

    print("\nMaster data generation completed!")
    print(f"Learner records: {len(learners)}")
    print(f"Course records: {len(courses)}")
    print(f"Output directory: {GENERATED_DIR}")


if __name__ == "__main__":
    main()
