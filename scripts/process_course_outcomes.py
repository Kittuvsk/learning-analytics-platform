
from sqlalchemy import text
from app.core.database import engine


def main():
    print("Starting course outcome processing...")

    with engine.begin() as conn:

        print("Step 1: Calculating enrollment engagement...")

        # Indexed enrollment join; aggregate only events with
        # matching enrollment IDs and valid learner/course pairs.
        conn.execute(text("""
            CREATE TEMPORARY TABLE tmp_engagement AS
            SELECT
                ev.enrollment_id,
                COUNT(DISTINCT ev.content_item_id) AS engaged_items
            FROM activity_events ev
            JOIN enrollments e
              ON e.enrollment_id = ev.enrollment_id
             AND e.learner_id = ev.learner_id
             AND e.course_id = ev.course_id
            JOIN content_items ci
              ON ci.content_item_id = ev.content_item_id
             AND ci.course_id = ev.course_id
             AND ci.content_status = 'PUBLISHED'
             AND ci.content_type <> 'MODULE'
            WHERE ev.enrollment_id IS NOT NULL
              AND ev.content_item_id IS NOT NULL
              AND ev.event_type NOT IN ('LOGIN', 'COURSE_OPENED')
              AND ev.source_event_id IS NULL
              AND ev.event_time_utc >= e.enrolled_at
              AND (
                  e.withdrawn_at IS NULL
                  OR ev.event_time_utc <= e.withdrawn_at
              )
            GROUP BY ev.enrollment_id
        """))

        print("Step 2: Calculating assessment progress...")

        conn.execute(text("""
            CREATE TEMPORARY TABLE tmp_assessments AS
            SELECT
                e.enrollment_id,
                COUNT(DISTINCT a.assessment_id) AS required_count,
                COUNT(DISTINCT CASE
                    WHEN latest.is_passed = 1
                     AND latest.score >= cr.minimum_assessment_score
                    THEN a.assessment_id
                END) AS passed_count,
                AVG(latest.score) AS average_score,
                COUNT(DISTINCT latest.assessment_id) AS graded_count
            FROM enrollments e
            LEFT JOIN completion_rules cr
              ON cr.course_id = e.course_id
             AND cr.rule_status = 'ACTIVE'
             AND cr.effective_from <= e.enrolled_at
            LEFT JOIN assessments a
              ON a.course_id = e.course_id
             AND a.assessment_status = 'PUBLISHED'
             AND a.is_required = 1
            LEFT JOIN (
                SELECT t1.*
                FROM attempts t1
                JOIN (
                    SELECT enrollment_id, assessment_id,
                           MAX(attempt_number) AS latest_attempt
                    FROM attempts
                    WHERE attempt_status = 'GRADED'
                    GROUP BY enrollment_id, assessment_id
                ) x
                  ON x.enrollment_id = t1.enrollment_id
                 AND x.assessment_id = t1.assessment_id
                 AND x.latest_attempt = t1.attempt_number
                WHERE t1.attempt_status = 'GRADED'
            ) latest
              ON latest.enrollment_id = e.enrollment_id
             AND latest.assessment_id = a.assessment_id
            GROUP BY e.enrollment_id
        """))

        print("Step 3: Saving outcomes...")

        conn.execute(text("""
            INSERT INTO course_outcomes (
                enrollment_id,
                completion_rule_id,
                content_completion_percentage,
                content_engagement_percentage,
                assessment_completion_percentage,
                final_assessment_score,
                outcome_status,
                calculated_at,
                completion_reason
            )
            SELECT
                e.enrollment_id,
                cr.completion_rule_id,
                NULL,
                CASE
                    WHEN COALESCE(ct.total_items, 0) = 0 THEN 0
                    ELSE ROUND(
                        100 * COALESCE(eg.engaged_items, 0)
                        / ct.total_items, 2
                    )
                END,
                CASE
                    WHEN COALESCE(ap.required_count, 0) = 0 THEN 0
                    ELSE ROUND(
                        100 * COALESCE(ap.passed_count, 0)
                        / ap.required_count, 2
                    )
                END,
                ROUND(ap.average_score, 2),
                CASE
                    WHEN e.enrollment_status = 'WITHDRAWN'
                        THEN 'WITHDRAWN'
                    WHEN e.enrollment_status = 'SUSPENDED'
                        THEN 'SUSPENDED'
                    WHEN COALESCE(eg.engaged_items, 0) > 0
                      OR COALESCE(ap.graded_count, 0) > 0
                        THEN 'IN_PROGRESS'
                    ELSE 'NOT_STARTED'
                END,
                UTC_TIMESTAMP(),
                CASE
                    WHEN e.enrollment_status = 'WITHDRAWN'
                        THEN 'Enrollment withdrawn'
                    WHEN e.enrollment_status = 'SUSPENDED'
                        THEN 'Enrollment suspended'
                    ELSE 'Content completion evidence unavailable'
                END
            FROM enrollments e
            LEFT JOIN completion_rules cr
              ON cr.course_id = e.course_id
             AND cr.rule_status = 'ACTIVE'
             AND cr.effective_from <= e.enrolled_at
            LEFT JOIN tmp_engagement eg
              ON eg.enrollment_id = e.enrollment_id
            LEFT JOIN (
                SELECT course_id, COUNT(*) AS total_items
                FROM content_items
                WHERE content_status = 'PUBLISHED'
                  AND content_type <> 'MODULE'
                GROUP BY course_id
            ) ct ON ct.course_id = e.course_id
            LEFT JOIN tmp_assessments ap
              ON ap.enrollment_id = e.enrollment_id
            ON DUPLICATE KEY UPDATE
                completion_rule_id = VALUES(completion_rule_id),
                content_completion_percentage = NULL,
                content_engagement_percentage =
                    VALUES(content_engagement_percentage),
                assessment_completion_percentage =
                    VALUES(assessment_completion_percentage),
                final_assessment_score =
                    VALUES(final_assessment_score),
                outcome_status = VALUES(outcome_status),
                calculated_at = VALUES(calculated_at),
                completion_reason = VALUES(completion_reason)
        """))

        total = conn.execute(text(
            "SELECT COUNT(*) FROM course_outcomes"
        )).scalar_one()

        expected = conn.execute(text(
            "SELECT COUNT(*) FROM enrollments"
        )).scalar_one()

        if total != expected:
            raise RuntimeError(
                f"Mismatch: {total} outcomes for {expected} enrollments"
            )

        print(f"Verified outcomes: {total:,}")
        print("Course outcome processing completed!")


if __name__ == "__main__":
    main()
