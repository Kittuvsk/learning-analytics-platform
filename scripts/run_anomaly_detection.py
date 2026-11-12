
from sqlalchemy import text
from app.core.database import engine


DETECTION_QUERIES = [
    {
        "issue_type": "DUPLICATE_EVENT",
        "severity": "HIGH",
        "description": "Duplicate activity event: source_event_id references an existing event.",
        "sql": """
            SELECT e.event_id
            FROM activity_events e
            INNER JOIN activity_events original
                ON original.event_id = e.source_event_id
            WHERE e.source_event_id IS NOT NULL
        """
    },
    {
        "issue_type": "UNENROLLED_ACTIVITY",
        "severity": "HIGH",
        "description": "Activity recorded without a matching learner-course enrollment.",
        "sql": """
            SELECT e.event_id
            FROM activity_events e
            WHERE NOT EXISTS (
                SELECT 1
                FROM enrollments en
                WHERE en.learner_id = e.learner_id
                  AND en.course_id = e.course_id
                  AND (
                      e.enrollment_id IS NULL
                      OR en.enrollment_id = e.enrollment_id
                  )
            )
        """
    },
    {
        "issue_type": "PREMATURE_COMPLETION",
        "severity": "CRITICAL",
        "description": "Course completion event occurred before the first assessment attempt.",
        "sql": """
            SELECT e.event_id
            FROM activity_events e
            LEFT JOIN (
                SELECT enrollment_id, MIN(started_at) AS first_attempt
                FROM attempts
                GROUP BY enrollment_id
            ) a ON a.enrollment_id = e.enrollment_id
            WHERE e.event_type = 'COURSE_COMPLETED'
              AND e.enrollment_id IS NOT NULL
              AND (
                  a.first_attempt IS NULL
                  OR a.first_attempt > e.event_time_utc
              )
        """
    }
]


def main():

    print("=" * 55)
    print("LEARNING ANALYTICS - ANOMALY DETECTION")
    print("=" * 55)

    with engine.begin() as connection:

        for rule in DETECTION_QUERIES:

            print(f"\nRunning: {rule['issue_type']}")

            query = text(rule["sql"])

            detected_ids = connection.execute(query).fetchall()

            print(f"Candidates found: {len(detected_ids):,}")

            if not detected_ids:
                continue

            records = [
                {
                    "issue_type": rule["issue_type"],
                    "entity_type": "ACTIVITY_EVENT",
                    "entity_id": row[0],
                    "severity": rule["severity"],
                    "description": rule["description"]
                }
                for row in detected_ids
            ]

            insert_sql = text("""
                INSERT INTO anomaly_records (
                    issue_type,
                    entity_type,
                    entity_id,
                    severity,
                    detection_status,
                    description,
                    detected_at
                )
                SELECT
                    :issue_type,
                    :entity_type,
                    :entity_id,
                    :severity,
                    'OPEN',
                    :description,
                    UTC_TIMESTAMP()
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM anomaly_records existing
                    WHERE existing.issue_type = :issue_type
                      AND existing.entity_type = :entity_type
                      AND existing.entity_id = :entity_id
                )
            """)

            inserted = 0

            batch_size = 1000

            for start in range(0, len(records), batch_size):

                batch = records[start:start + batch_size]

                result = connection.execute(insert_sql, batch)

                inserted += result.rowcount

            print(f"New anomaly records inserted: {inserted:,}")

    print("\n" + "=" * 55)
    print("ANOMALY DETECTION COMPLETED")
    print("Timezone detection is not included in this first pass.")
    print("=" * 55)


if __name__ == "__main__":
    main()
