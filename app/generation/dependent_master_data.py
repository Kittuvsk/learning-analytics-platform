
from datetime import date, datetime, timedelta

import pandas as pd
import numpy as np

from app.generation.config import (
    GenerationConfig,
    GENERATED_DIR,
    create_generators,
    create_data_directories,
)


AS_OF_DATE = date(2026, 11, 12)


def generate_cohorts(config, rng):

    records = []

    for i in range(1, config.cohort_count + 1):

        start = date(2025, 1, 1) + timedelta(
            days=rng.randint(0, 899)
        )

        end = start + timedelta(days=120)

        if start > AS_OF_DATE:
            status = "PLANNED"
        elif end < AS_OF_DATE:
            status = "COMPLETED"
        else:
            status = "ACTIVE"

        records.append({
            "cohort_id": i,
            "cohort_code": f"COH-2026-{i:03d}",
            "cohort_name": f"Learning Cohort {i:03d}",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "description": f"Synthetic learning cohort {i:03d}",
            "cohort_status": status,
        })

    return pd.DataFrame(records)


def generate_content(config, courses, rng):

    records = []

    content_types = [
        "VIDEO",
        "DOCUMENT",
        "ARTICLE",
        "QUIZ",
        "ASSIGNMENT",
        "VIDEO",
        "ARTICLE",
    ]

    content_id = 1
    assessment_content_map = {}

    for _, course in courses.iterrows():

        course_id = course["course_id"]
        course_status = course["course_status"]

        # One parent module per course.
        module_id = content_id

        records.append({
            "content_item_id": content_id,
            "course_id": course_id,
            "parent_content_item_id": None,
            "title": f"{course['course_name']} - Main Module",
            "content_type": "MODULE",
            "sequence_number": 1,
            "estimated_minutes": 0,
            "content_status": course_status,
        })

        content_id += 1

        quiz_id = None
        assignment_id = None

        # Seven child content items.
        for sequence, item_type in enumerate(
            content_types, start=1
        ):

            current_id = content_id

            records.append({
                "content_item_id": current_id,
                "course_id": course_id,
                "parent_content_item_id": module_id,
                "title": (
                    f"{course['course_name']} - "
                    f"{item_type.title()} {sequence}"
                ),
                "content_type": item_type,
                "sequence_number": sequence,
                "estimated_minutes": int(
                    rng.randint(5, 90)
                ),
                "content_status": course_status,
            })

            if item_type == "QUIZ":
                quiz_id = current_id

            if item_type == "ASSIGNMENT":
                assignment_id = current_id

            content_id += 1

        assessment_content_map[course_id] = {
            "quiz": quiz_id,
            "assignment": assignment_id,
        }

    return pd.DataFrame(records), assessment_content_map


def generate_completion_rules(courses, rng):

    records = []

    for i, course in courses.iterrows():

        course_status = course["course_status"]

        if course_status == "PUBLISHED":
            rule_status = "ACTIVE"
        elif course_status == "ARCHIVED":
            rule_status = "RETIRED"
        else:
            rule_status = "DRAFT"

        effective_from = course["published_at"]

        if pd.isna(effective_from):
            effective_from = "2025-01-01 00:00:00"

        records.append({
            "completion_rule_id": i + 1,
            "course_id": course["course_id"],
            "rule_version": 1,
            "minimum_content_completion": float(
                rng.choice([80.00, 90.00, 100.00])
            ),
            "require_all_assessments": 1,
            "minimum_assessment_score": 60.00,
            "effective_from": effective_from,
            "effective_to": None,
            "rule_status": rule_status,
        })

    return pd.DataFrame(records)


def generate_assessments(courses, assessment_content_map):

    records = []

    assessment_number = 1

    for _, course in courses.iterrows():

        course_id = course["course_id"]
        course_status = course["course_status"]

        if course_status == "PUBLISHED":
            assessment_status = "PUBLISHED"
        elif course_status == "ARCHIVED":
            assessment_status = "CLOSED"
        else:
            assessment_status = "DRAFT"

        available_from = course["published_at"]
        due_at = None

        if pd.notna(available_from):
            available_date = datetime.strptime(
                available_from,
                "%Y-%m-%d %H:%M:%S",
            )

            due_at = (
                available_date + timedelta(days=21)
            ).strftime("%Y-%m-%d %H:%M:%S")

        content_mapping = assessment_content_map[course_id]

        assessment_definitions = [
            {
                "type": "QUIZ",
                "title": f"{course['course_name']} - Final Quiz",
                "content_id": content_mapping["quiz"],
            },
            {
                "type": "ASSIGNMENT",
                "title": f"{course['course_name']} - Final Assignment",
                "content_id": content_mapping["assignment"],
            },
        ]

        for definition in assessment_definitions:

            records.append({
                "assessment_id": (
                    f"ASM-2026-{assessment_number:06d}"
                ),
                "course_id": course_id,
                "content_item_id": definition["content_id"],
                "title": definition["title"],
                "assessment_type": definition["type"],
                "maximum_score": 100.00,
                "passing_score": 60.00,
                "is_required": 1,
                "available_from": available_from,
                "due_at": due_at,
                "assessment_status": assessment_status,
            })

            assessment_number += 1

    return pd.DataFrame(records)


def validate_dependent_data(
    cohorts,
    courses,
    content,
    rules,
    assessments,
    config,
):

    errors = []

    # Cohort validation
    if len(cohorts) != config.cohort_count:
        errors.append("Cohort count mismatch")

    if cohorts["cohort_code"].duplicated().any():
        errors.append("Duplicate cohort codes")

    if not cohorts["cohort_status"].isin(
        ["PLANNED", "ACTIVE", "COMPLETED", "CANCELLED"]
    ).all():
        errors.append("Invalid cohort status")

    # Content validation
    if content["content_item_id"].duplicated().any():
        errors.append("Duplicate content item IDs")

    if not content["course_id"].isin(
        courses["course_id"]
    ).all():
        errors.append("Invalid content course reference")

    if not content["content_type"].isin([
        "VIDEO", "DOCUMENT", "ARTICLE",
        "QUIZ", "ASSIGNMENT", "MODULE"
    ]).all():
        errors.append("Invalid content type")

    parent_ids = content[
        "parent_content_item_id"
    ].dropna().astype(int)

    if not parent_ids.isin(
        content["content_item_id"]
    ).all():
        errors.append("Invalid content parent reference")

    # Completion rule validation
    if len(rules) != len(courses):
        errors.append("Completion rule count mismatch")

    if rules["course_id"].duplicated().any():
        errors.append("Duplicate course completion rules")

    if not rules["course_id"].isin(
        courses["course_id"]
    ).all():
        errors.append("Invalid completion rule course reference")

    # Assessment validation
    if assessments["assessment_id"].duplicated().any():
        errors.append("Duplicate assessment IDs")

    if not assessments["course_id"].isin(
        courses["course_id"]
    ).all():
        errors.append("Invalid assessment course reference")

    if not assessments["content_item_id"].isin(
        content["content_item_id"]
    ).all():
        errors.append("Invalid assessment content reference")

    if not assessments["assessment_type"].isin(
        ["QUIZ", "EXAM", "ASSIGNMENT", "PROJECT"]
    ).all():
        errors.append("Invalid assessment type")

    if (
        assessments["passing_score"]
        > assessments["maximum_score"]
    ).any():
        errors.append("Passing score exceeds maximum score")

    if errors:
        raise ValueError("\n".join(errors))

    print("Dependent master data validation: PASSED")


def main():

    config = GenerationConfig()

    create_data_directories()

    rng, numpy_rng, fake = create_generators(
        config.seed + 1
    )

    courses = pd.read_csv(
        GENERATED_DIR / "courses.csv"
    )

    print("Generating cohorts...")
    cohorts = generate_cohorts(config, rng)

    print("Generating course content...")
    content, assessment_content_map = generate_content(
        config, courses, rng
    )

    print("Generating completion rules...")
    rules = generate_completion_rules(courses, rng)

    print("Generating assessments...")
    assessments = generate_assessments(
        courses, assessment_content_map
    )

    print("Validating dependent master data...")

    validate_dependent_data(
        cohorts,
        courses,
        content,
        rules,
        assessments,
        config,
    )

    datasets = {
        "cohorts.csv": cohorts,
        "content_items.csv": content,
        "completion_rules.csv": rules,
        "assessments.csv": assessments,
    }

    for filename, dataframe in datasets.items():

        dataframe.to_csv(
            GENERATED_DIR / filename,
            index=False,
        )

        print(
            f"Saved {filename}: "
            f"{len(dataframe)} records"
        )

    print("\nDependent master data generation completed!")


if __name__ == "__main__":
    main()
