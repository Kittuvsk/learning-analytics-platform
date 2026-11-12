from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_permission
from app.api.routes.auth import get_db
from app.models.user import User
from app.schemas.auth import UserResponse


router = APIRouter(
    prefix="/admin",
    tags=["Administration"]
)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("USER_MANAGE")
    ),
):
    return db.scalars(
        select(User).order_by(User.user_id)
    ).all()