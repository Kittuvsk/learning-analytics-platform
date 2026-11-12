
from sqlalchemy import text
from app.core.database import engine


def main():
    print("Starting fast course outcome processing...")

    with engine.begin() as conn:

        print("Calculating latest graded attempts...")

        conn.execute(text("""
            CREATE TEMPORARY TABLE tmp_latest_attempt AS
            SELECT
                t.enrollment_id,
                t.assessment_id,
                t.score,
                t.is_passed
            FROM attempts t
            JOIN (
                SELECT
                    enrollment_id,
                    assessment_id,
                    MAX(attempt_number) AS latest_attempt
                FROM attempts
                WHERE attempt_status = 'GRADED'
                GROUP BY enrollment_id, assessment_id
            ) latest
              ON latest.enrollment_id = t.enrollment_id
             AND latest.assessment_id = t.assessment_id
             AND latest.latest_attempt = t.attempt_number
            WHERE t.attempt_status = 'GRADED'
        """))

        print("Calculating assessment progress...")

        conn.execute(text("""
            CREATE TEMPORARY TABLE tmp_assessment AS
            SELECT
                e.enrollment_id,
                COUNT(DISTINCT a.assessment_id) AS required_count,
                COUNT(DISTINCT CASE
                    WHEN la.is_passed = 1
                     AND la.score >= COALESCE(
                         cr.minimum_assessment_score, 60
                     )
                    THEN a.assessment_id
                END) AS passed_count,
                AVG(la.score) AS average_score,
                COUNT(DISTINCT la.assessment_id) AS graded_count
            FROM enrollments e
            LEFT JOIN completion_rules cr
              ON cr.course_id = e.course_id
             AND cr.rule_status = 'ACTIVE'
             AND cr.effective_from <= e.enrolled_at
            LEFT JOIN assessments a
              ON a.course_id = e.course_id
             AND a.assessment_status = 'PUBLISHED'
             AND a.is_required = 1
            LEFT JOIN tmp_latest_attempt la
              ON la.enrollment_id = e.enrollment_id
             AND la.assessment_id = a.assessment_id
            GROUP BY e.enrollment_id
        """))

        print("Saving course outcomes...")

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
                0,
                CASE
                    WHEN COALESCE(ap.required_count, 0) = 0 THEN 0
                    ELSE ROUND(
                        100.0 * ap.passed_count / ap.required_count, 2
                    )
                END,
                ROUND(ap.average_score, 2),
                CASE
                    WHEN e.enrollment_status = 'WITHDRAWN'
                        THEN 'WITHDRAWN'
                    WHEN e.enrollment_status = 'SUSPENDED'
                        THEN 'SUSPENDED'
                    WHEN COALESCE(ap.graded_count, 0) > 0
                        THEN 'IN_PROGRESS'
                    WHEN EXISTS (
                        SELECT 1
                        FROM activity_events ev
                        WHERE ev.enrollment_id = e.enrollment_id
                        LIMIT 1
                    )
                        THEN 'IN_PROGRESS'
                    ELSE 'NOT_STARTED'
                END,
                UTC_TIMESTAMP(),
                CASE
                    WHEN e.enrollment_status = 'WITHDRAWN'
                        THEN 'Enrollment withdrawn'
                    WHEN e.enrollment_status = 'SUSPENDED'
                        THEN 'Enrollment suspended'
                    ELSE 'Content completion and engagement not calculated'
                END
            FROM enrollments e
            LEFT JOIN completion_rules cr
              ON cr.course_id = e.course_id
             AND cr.rule_status = 'ACTIVE'
             AND cr.effective_from <= e.enrolled_at
            LEFT JOIN tmp_assessment ap
              ON ap.enrollment_id = e.enrollment_id
            ON DUPLICATE KEY UPDATE
                completion_rule_id = VALUES(completion_rule_id),
                content_completion_percentage = NULL,
                content_engagement_percentage = 0,
                assessment_completion_percentage =
                    VALUES(assessment_completion_percentage),
                final_assessment_score = VALUES(final_assessment_score),
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
                f"Expected {expected} outcomes but found {total}"
            )

        print(f"Verified outcomes: {total:,}")
        print("Fast outcome processing completed successfully.")


if __name__ == "__main__":
    main()
