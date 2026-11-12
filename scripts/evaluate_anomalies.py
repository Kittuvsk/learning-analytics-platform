
from sqlalchemy import text
from app.core.database import engine


QUERY = text("""
    SELECT
        gt.issue_type,

        SUM(
            CASE
                WHEN gt.expected_label = 1
                 AND ar.anomaly_id IS NOT NULL
                THEN 1 ELSE 0
            END
        ) AS true_positives,

        SUM(
            CASE
                WHEN gt.expected_label = 1
                 AND ar.anomaly_id IS NULL
                THEN 1 ELSE 0
            END
        ) AS false_negatives

    FROM ground_truth gt

    LEFT JOIN anomaly_records ar
        ON ar.entity_type = gt.entity_type
       AND ar.entity_id = gt.entity_id
       AND ar.issue_type = gt.issue_type

    GROUP BY gt.issue_type
    ORDER BY gt.issue_type
""")


def main():

    with engine.connect() as connection:
        rows = connection.execute(QUERY).mappings().all()

    print("\nANOMALY DETECTION EVALUATION")
    print("=" * 75)

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for row in rows:

        issue = row["issue_type"]
        tp = int(row["true_positives"] or 0)
        fn = int(row["false_negatives"] or 0)

        detected = connection_count(issue)
        fp = detected - tp

        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0
        )

        total_tp += tp
        total_fp += fp
        total_fn += fn

        print(f"\n{issue}")
        print(f"TP: {tp}")
        print(f"FP: {fp}")
        print(f"FN: {fn}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1 Score:  {f1:.4f}")

    precision = (
        total_tp / (total_tp + total_fp)
        if total_tp + total_fp else 0
    )

    recall = (
        total_tp / (total_tp + total_fn)
        if total_tp + total_fn else 0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    print("\n" + "=" * 75)
    print("OVERALL EVALUATION")
    print(f"TP: {total_tp}")
    print(f"FP: {total_fp}")
    print(f"FN: {total_fn}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")


def connection_count(issue):

    with engine.connect() as connection:
        return connection.execute(
            text("""
                SELECT COUNT(*)
                FROM anomaly_records
                WHERE issue_type = :issue
                  AND entity_type = 'ACTIVITY_EVENT'
            """),
            {"issue": issue}
        ).scalar_one()


if __name__ == "__main__":
    main()
