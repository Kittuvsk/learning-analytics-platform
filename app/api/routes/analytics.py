
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session

from app.api.routes.auth import get_db, get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check the user's analytics permissions.
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
        # Platform and academic administrators.
        query = text("""
            SELECT
                (SELECT COUNT(*) FROM learners)
                    AS total_learners,

                (SELECT COUNT(*)
                 FROM learners
                 WHERE learner_status = 'ACTIVE')
                    AS active_learners,

                (SELECT COUNT(*) FROM courses)
                    AS total_courses,

                (SELECT COUNT(*)
                 FROM courses
                 WHERE course_status = 'PUBLISHED')
                    AS published_courses,

                (SELECT COUNT(*) FROM enrollments)
                    AS total_enrollments,

                (SELECT COUNT(DISTINCT learner_id)
                 FROM enrollments)
                    AS enrolled_learners
        """)

        scope = "ALL"

    elif "ANALYTICS_READ_ASSIGNED" in permissions:
        # Instructors see only their assigned courses.
        query = text("""
            SELECT
                COUNT(DISTINCT l.learner_id)
                    AS total_learners,

                COUNT(DISTINCT CASE
                    WHEN l.learner_status = 'ACTIVE'
                    THEN l.learner_id
                END) AS active_learners,

                COUNT(DISTINCT c.course_id)
                    AS total_courses,

                COUNT(DISTINCT CASE
                    WHEN c.course_status = 'PUBLISHED'
                    THEN c.course_id
                END) AS published_courses,

                COUNT(DISTINCT e.enrollment_id)
                    AS total_enrollments,

                COUNT(DISTINCT e.learner_id)
                    AS enrolled_learners

            FROM instructor_courses ic

            JOIN courses c
                ON c.course_id = ic.course_id

            LEFT JOIN enrollments e
                ON e.course_id = c.course_id

            LEFT JOIN learners l
                ON l.learner_id = e.learner_id

            WHERE ic.instructor_user_id = :user_id
        """)

        scope = "ASSIGNED_COURSES"

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics permission required",
        )

    result = db.execute(
        query,
        {"user_id": current_user.user_id},
    ).mappings().one()

    return {
        "scope": scope,
        "metrics": {
            key: int(value or 0)
            for key, value in result.items()
        },
    }
