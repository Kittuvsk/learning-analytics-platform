
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth import get_db
from app.core.rbac import require_permission
from app.models.user import User


router = APIRouter(tags=["Resource Access"])


@router.get("/instructor/courses")
def get_assigned_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("COURSE_READ_ASSIGNED")
    ),
):
    query = text("""
        SELECT
            c.course_id,
            c.course_name,
            c.category,
            c.course_status
        FROM instructor_courses ic
        JOIN courses c
            ON c.course_id = ic.course_id
        WHERE ic.instructor_user_id = :user_id
        ORDER BY c.course_name
    """)

    result = db.execute(
        query,
        {"user_id": current_user.user_id}
    )

    return [dict(row) for row in result.mappings().all()]


@router.get("/instructor/courses/{course_id}/enrollments")
def get_course_enrollments(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("COURSE_READ_ASSIGNED")
    ),
):
    query = text("""
        SELECT
            e.enrollment_id,
            e.learner_id,
            l.first_name,
            l.last_name,
            e.enrollment_status,
            e.enrolled_at
        FROM instructor_courses ic
        JOIN enrollments e
            ON e.course_id = ic.course_id
        JOIN learners l
            ON l.learner_id = e.learner_id
        WHERE ic.instructor_user_id = :user_id
          AND ic.course_id = :course_id
        ORDER BY e.enrolled_at DESC
    """)

    result = db.execute(
        query,
        {
            "user_id": current_user.user_id,
            "course_id": course_id,
        }
    )

    rows = [dict(row) for row in result.mappings().all()]

    if not rows:
        # Do not reveal whether an unassigned course exists.
        raise HTTPException(
            status_code=404,
            detail="Course not found or not assigned to instructor"
        )

    return rows


@router.get("/learner/enrollments")
def get_learner_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("LEARNER_READ_OWN")
    ),
):
    query = text("""
        SELECT
            e.enrollment_id,
            e.course_id,
            c.course_name,
            e.enrollment_status,
            e.enrolled_at,
            e.started_at,
            e.completed_at
        FROM learners l
        JOIN enrollments e
            ON e.learner_id = l.learner_id
        JOIN courses c
            ON c.course_id = e.course_id
        WHERE l.user_id = :user_id
        ORDER BY e.enrolled_at DESC
    """)

    result = db.execute(
        query,
        {"user_id": current_user.user_id}
    )

    return [dict(row) for row in result.mappings().all()]
