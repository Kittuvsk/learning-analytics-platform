
import argparse
import csv
from pathlib import Path

from sqlalchemy import text

from app.core.database import engine


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"

BATCH_SIZE = 5000

# Insert order respects foreign-key relationships.
TABLES = [
    ("learners", "learners.csv"),
    ("courses", "courses.csv"),
    ("cohorts", "cohorts.csv"),
    ("content_items", "content_items.csv"),
    ("completion_rules", "completion_rules.csv"),
    ("assessments", "assessments.csv"),
    ("enrollments", "enrollments.csv"),
    ("attempts", "attempts.csv"),
    ("activity_events", "activity_events.csv"),
]

INTEGER_COLUMNS = {
    "user_id",
    "cohort_id",
    "content_item_id",
    "parent_content_item_id",
    "completion_rule_id",
    "rule_version",
    "sequence_number",
    "estimated_minutes",
    "require_all_assessments",
    "is_required",
    "attempt_number",
    "is_passed",
    "duration_seconds",
    "is_late_event",
}

FLOAT_COLUMNS = {
    "minimum_content_completion",
    "minimum_assessment_score",
    "maximum_score",
    "passing_score",
    "score",
    "duration_hours",
}

def convert_value(column, value):
    if value is None:
        return None

    value = value.strip()

    if value.lower() in ("", "nan", "none", "null"):
        return None

    if column in INTEGER_COLUMNS:
        return int(float(value))

    if column in FLOAT_COLUMNS:
        return float(value)

    # MySQL accepts standard datetime/date strings.
    return value


def load_table(connection, table, filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    total = 0

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        columns = reader.fieldnames

        if not columns:
            raise ValueError(f"No CSV headers found: {filename}")

        column_sql = ", ".join(f"`{c}`" for c in columns)
        parameter_sql = ", ".join(f":{c}" for c in columns)

        statement = text(
            f"INSERT INTO `{table}` "
            f"({column_sql}) VALUES ({parameter_sql})"
        )

        batch = []

        for row in reader:
            converted = {
                column: convert_value(column, value)
                for column, value in row.items()
            }

            batch.append(converted)

            if len(batch) >= BATCH_SIZE:
                connection.execute(statement, batch)
                total += len(batch)
                batch.clear()

                print(f"{table}: {total:,} rows inserted", flush=True)

        if batch:
            connection.execute(statement, batch)
            total += len(batch)

    print(f"{table}: completed ({total:,} rows)", flush=True)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-events",
        action="store_true",
        help="Load activity events after validation.",
    )
    args = parser.parse_args()

    tables = TABLES if args.include_events else TABLES[:-1]

    print("Starting MySQL bulk loading...")
    print("Activity events included:", args.include_events)

    totals = {}

    # All selected tables are loaded in one transaction.
    # Any error rolls back the entire loading operation.
    with engine.begin() as connection:
        for table, filename in tables:
            print(f"\nLoading {table}...")

            count = load_table(
                connection,
                table,
                filename,
            )

            totals[table] = count

    print("\n====================================")
    print("DATABASE LOADING COMPLETED")
    print("====================================")

    for table, count in totals.items():
        print(f"{table}: {count:,}")

    print("Transaction committed successfully.")


if __name__ == "__main__":
    main()
