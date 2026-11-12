
import csv
from pathlib import Path

from sqlalchemy import text

from app.core.database import engine


ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "data" / "generated" / "activity_events.csv"

BATCH_SIZE = 5000
EXPECTED_ROWS = 2_000_000

COLUMNS = [
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

INTEGER_COLUMNS = {
    "content_item_id",
    "duration_seconds",
    "is_late_event",
}


def convert_row(row):
    result = {}

    for column in COLUMNS:
        value = row[column]

        if value is None or value.strip().lower() in (
            "", "nan", "none", "null"
        ):
            result[column] = None
        elif column in INTEGER_COLUMNS:
            result[column] = int(float(value))
        else:
            result[column] = value

    return result


def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(CSV_FILE)

    print("Checking activity event CSV...")

    with CSV_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != COLUMNS:
            raise ValueError(
                f"Unexpected CSV columns: {reader.fieldnames}"
            )

    print("CSV headers validated.")

    total = 0

    column_sql = ", ".join(f"`{c}`" for c in COLUMNS)
    parameter_sql = ", ".join(f":{c}" for c in COLUMNS)

    statement = text(
        f"INSERT INTO activity_events "
        f"({column_sql}) VALUES ({parameter_sql})"
    )

    print("Starting activity event loading...")
    print(f"Target rows: {EXPECTED_ROWS:,}")

    # One transaction: failure rolls back the complete load.
    with engine.begin() as connection:

        existing = connection.execute(
            text("SELECT COUNT(*) FROM activity_events")
        ).scalar_one()

        if existing != 0:
            raise RuntimeError(
                f"Activity table already has {existing:,} rows. "
                "Load cancelled to prevent duplicates."
            )

        with CSV_FILE.open(
            "r", newline="", encoding="utf-8-sig"
        ) as file:
            reader = csv.DictReader(file)

            batch = []

            for row in reader:
                batch.append(convert_row(row))

                if len(batch) >= BATCH_SIZE:
                    connection.execute(statement, batch)
                    total += len(batch)
                    batch.clear()

                    if total % 100_000 == 0:
                        print(
                            f"Inserted {total:,} / "
                            f"{EXPECTED_ROWS:,}",
                            flush=True,
                        )

            if batch:
                connection.execute(statement, batch)
                total += len(batch)

        if total != EXPECTED_ROWS:
            raise ValueError(
                f"Expected {EXPECTED_ROWS:,}, loaded {total:,}"
            )

        database_count = connection.execute(
            text("SELECT COUNT(*) FROM activity_events")
        ).scalar_one()

        if database_count != EXPECTED_ROWS:
            raise ValueError(
                f"Database count mismatch: {database_count:,}"
            )

    print("\n======================================")
    print("ACTIVITY EVENT LOADING COMPLETED")
    print("======================================")
    print(f"CSV rows loaded: {total:,}")
    print(f"MySQL rows verified: {database_count:,}")
    print("Transaction committed successfully.")


if __name__ == "__main__":
    main()
