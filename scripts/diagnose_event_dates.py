
import pandas as pd

from app.generation.config import GENERATED_DIR, GROUND_TRUTH_DIR

events_file = GENERATED_DIR / "activity_events.csv"
enrollments_file = GENERATED_DIR / "enrollments.csv"
truth_file = GROUND_TRUTH_DIR / "ground_truth.csv"

enrollments = pd.read_csv(enrollments_file)
truth = pd.read_csv(truth_file)

enrollments["enrolled_at"] = pd.to_datetime(
    enrollments["enrolled_at"],
    errors="coerce",
)

enrollment_dates = enrollments.set_index(
    "enrollment_id"
)["enrolled_at"]

truth_map = truth.set_index(
    "entity_id"
)["issue_type"].to_dict()

total_affected = 0
examples = []

print("Checking event timestamps in batches...")

for chunk in pd.read_csv(
    events_file,
    chunksize=100_000,
    dtype={
        "event_id": "string",
        "enrollment_id": "string",
    },
):
    chunk["event_time_utc"] = pd.to_datetime(
        chunk["event_time_utc"],
        errors="coerce",
    )

    enrolled = chunk[
        chunk["enrollment_id"].notna()
    ].copy()

    enrolled["enrolled_at"] = enrolled[
        "enrollment_id"
    ].map(enrollment_dates)

    enrolled["issue_type"] = enrolled[
        "event_id"
    ].map(truth_map)

    invalid = enrolled[
        (enrolled["event_time_utc"] < enrolled["enrolled_at"])
        & (
            enrolled["issue_type"]
            != "TIMEZONE_MISALIGNMENT"
        )
    ]

    total_affected += len(invalid)

    if len(examples) < 20:
        examples.extend(
            invalid.head(20 - len(examples)).to_dict("records")
        )

print("\nTotal affected ordinary events:", total_affected)

if examples:
    print("\nFirst affected records:")

    for row in examples:
        print({
            "event_id": row["event_id"],
            "enrollment_id": row["enrollment_id"],
            "event_time_utc": str(row["event_time_utc"]),
            "enrolled_at": str(row["enrolled_at"]),
            "issue_type": row["issue_type"],
        })
else:
    print("No affected ordinary events found.")
