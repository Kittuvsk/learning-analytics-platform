
import pandas as pd
from sqlalchemy import text

from app.core.database import engine

CSV_PATH = "data/ground_truth/ground_truth.csv"

COLUMNS = [
    "issue_type",
    "entity_type",
    "entity_id",
    "expected_label",
    "expected_value",
    "explanation",
    "generator_seed",
]

def main():

    print("Checking ground-truth CSV...")

    df = pd.read_csv(CSV_PATH)

    if len(df) != 20000:
        raise ValueError(f"Expected 20000 records, found {len(df)}")

    if list(df.columns) != COLUMNS:
        raise ValueError("Ground-truth CSV columns do not match.")

    if df["entity_id"].duplicated().any():
        raise ValueError("Duplicate ground-truth entity IDs found.")

    print("CSV validation passed.")

    records = df[COLUMNS].astype(object).where(
        pd.notna(df[COLUMNS]), None
    ).to_dict(orient="records")

    insert_sql = text("""
        INSERT INTO ground_truth (
            issue_type,
            entity_type,
            entity_id,
            expected_label,
            expected_value,
            explanation,
            generator_seed
        )
        VALUES (
            :issue_type,
            :entity_type,
            :entity_id,
            :expected_label,
            :expected_value,
            :explanation,
            :generator_seed
        )
    """)

    print("Loading ground-truth records...")

    with engine.begin() as connection:

        existing = connection.execute(
            text("SELECT COUNT(*) FROM ground_truth")
        ).scalar_one()

        if existing != 0:
            raise RuntimeError(
                f"Ground-truth table already contains {existing} rows. "
                "Aborting to prevent duplicate loading."
            )

        batch_size = 1000

        for start in range(0, len(records), batch_size):

            batch = records[start:start + batch_size]

            connection.execute(insert_sql, batch)

            print(
                f"Inserted {min(start + batch_size, len(records))}"
                f" / {len(records)}"
            )

        total = connection.execute(
            text("SELECT COUNT(*) FROM ground_truth")
        ).scalar_one()

        if total != 20000:
            raise RuntimeError(
                f"Expected 20000 database records, found {total}"
            )

    print("\nGROUND-TRUTH LOADING COMPLETED")
    print(f"Verified MySQL records: {total}")
    print("Transaction committed successfully.")


if __name__ == "__main__":
    main()
