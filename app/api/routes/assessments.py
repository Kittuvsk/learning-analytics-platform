
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth import get_db, get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/assessments")
def get_assessment_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission_query = text("""
        SELECT DISTINCT p.permission_code
        FROM user_roles ur
        JOIN roles r ON r.role_id = ur.role_id
        JOIN role_permissions rp ON rp.role_id = r.role_id
        JOIN permissions p
            ON p.permission_id = rp.permission_id
        WHERE ur.user_id = :user_id
          AND p.permission_code IN (
              'ANALYTICS_READ_ALL',
              'ANALYTICS_READ_ASSIGNED'
          )
    """)

    permissions = set(
        db.execute(
            permission_query,
            {"user_id": current_user.user_id},
        ).scalars().all()
    )

    if "ANALYTICS_READ_ALL" in permissions:
        course_filter = ""
        scope = "ALL"

    elif "ANALYTICS_READ_ASSIGNED" in permissions:
        course_filter = """
            AND EXISTS (
                SELECT 1
                FROM instructor_courses ic
                WHERE ic.course_id = a.course_id
                  AND ic.instructor_user_id = :user_id
            )
        """
        scope = "ASSIGNED_COURSES"

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics permission required",
        )

    params = {"user_id": current_user.user_id}

    totals_query = text(f"""
        SELECT
            COUNT(DISTINCT a.assessment_id) AS total_assessments,

            COUNT(DISTINCT CASE
                WHEN a.assessment_status = 'PUBLISHED'
                THEN a.assessment_id
            END) AS published_assessments,

            COUNT(DISTINCT CASE
                WHEN a.assessment_status = 'DRAFT'
                THEN a.assessment_id
            END) AS draft_assessments,

            COUNT(DISTINCT CASE
                WHEN a.assessment_status = 'CLOSED'
                THEN a.assessment_id
            END) AS closed_assessments,

            COUNT(DISTINCT CASE
                WHEN a.is_required = 1
                THEN a.assessment_id
            END) AS required_assessments,

            COUNT(t.attempt_id) AS total_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'GRADED'
                THEN 1 ELSE 0
            END) AS graded_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'SUBMITTED'
                THEN 1 ELSE 0
            END) AS submitted_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'IN_PROGRESS'
                THEN 1 ELSE 0
            END) AS in_progress_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'ABANDONED'
                THEN 1 ELSE 0
            END) AS abandoned_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'GRADED'
                 AND t.is_passed = 1
                THEN 1 ELSE 0
            END) AS passed_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'GRADED'
                 AND t.is_passed = 0
                THEN 1 ELSE 0
            END) AS failed_attempts,

            AVG(CASE
                WHEN t.attempt_status = 'GRADED'
                THEN t.score
            END) AS average_score

        FROM assessments a
        LEFT JOIN attempts t
            ON t.assessment_id = a.assessment_id
        WHERE 1 = 1
        {course_filter}
    """)

    type_query = text(f"""
        SELECT
            a.assessment_type,
            COUNT(DISTINCT a.assessment_id) AS assessment_count,
            COUNT(t.attempt_id) AS total_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'GRADED'
                THEN 1 ELSE 0
            END) AS graded_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'GRADED'
                 AND t.is_passed = 1
                THEN 1 ELSE 0
            END) AS passed_attempts,

            SUM(CASE
                WHEN t.attempt_status = 'GRADED'
                 AND t.is_passed = 0
                THEN 1 ELSE 0
            END) AS failed_attempts,

            AVG(CASE
                WHEN t.attempt_status = 'GRADED'
                THEN t.score
            END) AS average_score

        FROM assessments a
        LEFT JOIN attempts t
            ON t.assessment_id = a.assessment_id
        WHERE 1 = 1
        {course_filter}
        GROUP BY a.assessment_type
        ORDER BY a.assessment_type
    """)

    status_query = text(f"""
        SELECT
            a.assessment_status,
            COUNT(DISTINCT a.assessment_id) AS assessment_count
        FROM assessments a
        WHERE 1 = 1
        {course_filter}
        GROUP BY a.assessment_status
        ORDER BY a.assessment_status
    """)

    totals = db.execute(
        totals_query, params
    ).mappings().one()

    type_rows = db.execute(
        type_query, params
    ).mappings().all()

    status_rows = db.execute(
        status_query, params
    ).mappings().all()

    passed = int(totals["passed_attempts"] or 0)
    failed = int(totals["failed_attempts"] or 0)
    evaluated_attempts = passed + failed

    pass_rate = (
        round((passed / evaluated_attempts) * 100, 2)
        if evaluated_attempts
        else 0.0
    )

    metrics = {
        key: int(value or 0)
        for key, value in totals.items()
        if key != "average_score"
    }

    metrics["average_score"] = (
        round(float(totals["average_score"]), 2)
        if totals["average_score"] is not None
        else None
    )
    metrics["pass_rate_percent"] = pass_rate

    by_type = []

    for row in type_rows:
        type_passed = int(row["passed_attempts"] or 0)
        type_failed = int(row["failed_attempts"] or 0)
        type_evaluated = type_passed + type_failed

        by_type.append({
            "assessment_type": row["assessment_type"],
            "assessment_count": int(row["assessment_count"] or 0),
            "total_attempts": int(row["total_attempts"] or 0),
            "graded_attempts": int(row["graded_attempts"] or 0),
            "passed_attempts": type_passed,
            "failed_attempts": type_failed,
            "average_score": (
                round(float(row["average_score"]), 2)
                if row["average_score"] is not None
                else None
            ),
            "pass_rate_percent": (
                round((type_passed / type_evaluated) * 100, 2)
                if type_evaluated
                else 0.0
            ),
        })

    by_status = [
        {
            "assessment_status": row["assessment_status"],
            "assessment_count": int(row["assessment_count"] or 0),
        }
        for row in status_rows
    ]

    return {
        "scope": scope,
        "metrics": metrics,
        "by_type": by_type,
        "by_status": by_status,
    }
