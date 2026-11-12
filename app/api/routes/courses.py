
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth import get_db, get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/courses")
def get_course_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission_query = text("""
        SELECT DISTINCT p.permission_code
        FROM user_roles ur
        JOIN roles r ON r.role_id = ur.role_id
        JOIN role_permissions rp ON rp.role_id = r.role_id
        JOIN permissions p ON p.permission_id = rp.permission_id
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
        scope = "ALL"
        assignment_filter = ""
        params = {}

    elif "ANALYTICS_READ_ASSIGNED" in permissions:
        scope = "ASSIGNED_COURSES"
        assignment_filter = """
            WHERE EXISTS (
                SELECT 1
                FROM instructor_courses ic
                WHERE ic.course_id = c.course_id
                  AND ic.instructor_user_id = :user_id
            )
        """
        params = {"user_id": current_user.user_id}

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics permission required",
        )

    query = text(f"""
        SELECT
            c.course_id,
            c.course_name,
            c.category,
            c.difficulty_level,
            c.course_status,
            c.duration_hours,

            COUNT(DISTINCT e.enrollment_id)
                AS total_enrollments,

            COUNT(DISTINCT CASE
                WHEN e.enrollment_status IN ('ENROLLED', 'IN_PROGRESS')
                THEN e.enrollment_id
            END) AS active_enrollments,

            COUNT(DISTINCT CASE
                WHEN e.enrollment_status = 'WITHDRAWN'
                THEN e.enrollment_id
            END) AS withdrawn_enrollments,

            COUNT(DISTINCT CASE
                WHEN e.enrollment_status = 'SUSPENDED'
                THEN e.enrollment_id
            END) AS suspended_enrollments,

            COUNT(DISTINCT CASE
                WHEN co.outcome_status = 'COMPLETED'
                THEN co.enrollment_id
            END) AS completed_learners

        FROM courses c

        LEFT JOIN enrollments e
            ON e.course_id = c.course_id

        LEFT JOIN course_outcomes co
            ON co.enrollment_id = e.enrollment_id

        {assignment_filter}

        GROUP BY
            c.course_id,
            c.course_name,
            c.category,
            c.difficulty_level,
            c.course_status,
            c.duration_hours

        ORDER BY c.course_name
    """)

    rows = db.execute(query, params).mappings().all()

    courses = []
    for row in rows:
        courses.append({
            "course_id": row["course_id"],
            "course_name": row["course_name"],
            "category": row["category"],
            "difficulty_level": row["difficulty_level"],
            "course_status": row["course_status"],
            "duration_hours": float(row["duration_hours"] or 0),
            "total_enrollments": int(row["total_enrollments"] or 0),
            "active_enrollments": int(row["active_enrollments"] or 0),
            "withdrawn_enrollments": int(row["withdrawn_enrollments"] or 0),
            "suspended_enrollments": int(row["suspended_enrollments"] or 0),
            "completed_learners": int(row["completed_learners"] or 0),
        })

    return {
        "scope": scope,
        "total_courses": len(courses),
        "courses": courses,
    }
