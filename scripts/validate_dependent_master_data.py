
import pandas as pd

from app.generation.config import GENERATED_DIR


def main():

    cohorts = pd.read_csv(GENERATED_DIR / "cohorts.csv")
    courses = pd.read_csv(GENERATED_DIR / "courses.csv")
    content = pd.read_csv(GENERATED_DIR / "content_items.csv")
    rules = pd.read_csv(GENERATED_DIR / "completion_rules.csv")
    assessments = pd.read_csv(GENERATED_DIR / "assessments.csv")

    errors = []

    # 1. Every course must have exactly 8 content items.
    content_counts = content.groupby("course_id").size()

    if len(content_counts) != len(courses):
        errors.append("Some courses have no content items")

    if not (content_counts == 8).all():
        errors.append("Incorrect content count per course")

    # 2. Each course must have one root module.
    roots = content[content["parent_content_item_id"].isna()]

    root_counts = roots.groupby("course_id").size()

    if not (root_counts == 1).all():
        errors.append("Each course must have exactly one root module")

    if not (roots["content_type"] == "MODULE").all():
        errors.append("Root content items must be MODULE")

    # 3. Every child must reference a module in its own course.
    children = content[
        content["parent_content_item_id"].notna()
    ].copy()

    children["parent_content_item_id"] = (
        children["parent_content_item_id"].astype(int)
    )

    parent_lookup = content.set_index("content_item_id")

    for _, child in children.iterrows():

        parent_id = child["parent_content_item_id"]

        if parent_id not in parent_lookup.index:
            errors.append(
                f"Missing parent for content {child['content_item_id']}"
            )
            continue

        parent = parent_lookup.loc[parent_id]

        if parent["course_id"] != child["course_id"]:
            errors.append(
                f"Cross-course parent reference: {child['content_item_id']}"
            )

        if parent["content_type"] != "MODULE":
            errors.append(
                f"Parent is not a MODULE: {child['content_item_id']}"
            )

    # 4. Assessment content type must match assessment type.
    content_lookup = content.set_index("content_item_id")

    for _, assessment in assessments.iterrows():

        content_id = int(assessment["content_item_id"])

        if content_id not in content_lookup.index:
            errors.append(
                f"Missing assessment content: {assessment['assessment_id']}"
            )
            continue

        item = content_lookup.loc[content_id]

        if item["course_id"] != assessment["course_id"]:
            errors.append(
                f"Assessment course mismatch: {assessment['assessment_id']}"
            )

        if item["content_type"] != assessment["assessment_type"]:
            errors.append(
                f"Assessment content type mismatch: {assessment['assessment_id']}"
            )

    # 5. Exactly one completion rule per course.
    rule_counts = rules.groupby("course_id").size()

    if len(rule_counts) != len(courses):
        errors.append("Some courses have no completion rule")

    if not (rule_counts == 1).all():
        errors.append("Duplicate completion rules found")

    # 6. Rule status must match course lifecycle.
    merged = rules.merge(
        courses[["course_id", "course_status"]],
        on="course_id",
        how="left",
        validate="one_to_one",
    )

    expected_status = {
        "PUBLISHED": "ACTIVE",
        "DRAFT": "DRAFT",
        "ARCHIVED": "RETIRED",
    }

    for _, row in merged.iterrows():

        if expected_status[row["course_status"]] != row["rule_status"]:
            errors.append(
                f"Incorrect rule status: {row['course_id']}"
            )

    # 7. Validate cohort date ordering.
    cohorts["start_date"] = pd.to_datetime(cohorts["start_date"])
    cohorts["end_date"] = pd.to_datetime(cohorts["end_date"])

    invalid_cohorts = cohorts[
        cohorts["end_date"] < cohorts["start_date"]
    ]

    if not invalid_cohorts.empty:
        errors.append("Invalid cohort date ranges")

    # 8. Assessment due date must not precede availability.
    available = pd.to_datetime(
        assessments["available_from"],
        errors="coerce",
    )

    due = pd.to_datetime(
        assessments["due_at"],
        errors="coerce",
    )

    invalid_due = available.notna() & (
        due.isna() | (due < available)
    )

    if invalid_due.any():
        errors.append("Invalid assessment date ordering")

    if errors:

        print("\nDEPENDENT DATA VALIDATION FAILED")

        for error in errors:
            print("-", error)

        raise SystemExit(1)

    print("\nALL DEPENDENT DATA INTEGRITY CHECKS PASSED!")

    print("Courses with 8 content items:", len(content_counts))
    print("Root modules:", len(roots))
    print("Child content items:", len(children))
    print("Valid assessments:", len(assessments))
    print("Valid completion rules:", len(rules))
    print("Valid cohorts:", len(cohorts))


if __name__ == "__main__":
    main()
