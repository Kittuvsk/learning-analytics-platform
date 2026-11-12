
import pandas as pd

from app.generation.config import GENERATED_DIR

file_path = GENERATED_DIR / "activity_events.csv"

total_invalid = 0

for number, chunk in enumerate(
    pd.read_csv(
        file_path,
        chunksize=100_000,
        dtype={
            "event_id": "string",
            "event_time_utc": "string",
            "received_at_utc": "string",
        },
    ),
    start=1,
):

    event_time = pd.to_datetime(
        chunk["event_time_utc"],
        format="mixed",
        errors="coerce",
    )

    received_time = pd.to_datetime(
        chunk["received_at_utc"],
        format="mixed",
        errors="coerce",
    )

    invalid = (
        event_time.isna()
        | received_time.isna()
    )

    bad = chunk[invalid].copy()

    if not bad.empty:

        total_invalid += len(bad)

        print(f"\nInvalid timestamps in chunk {number}:")
        print(
            bad[
                [
                    "event_id",
                    "event_time_utc",
                    "received_at_utc",
                ]
            ].head(20).to_string(index=False)
        )

print("\nTotal invalid timestamp rows:", total_invalid)
