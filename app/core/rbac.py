
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user, get_db
from app.models.user import (
    User,
    UserRole,
    Role,
    RolePermission,
    Permission,
)


def require_permission(permission_code: str):

    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:

        statement = (
            select(Permission.permission_id)
            .select_from(UserRole)
            .join(Role, Role.role_id == UserRole.role_id)
            .join(
                RolePermission,
                RolePermission.role_id == Role.role_id
            )
            .join(
                Permission,
                Permission.permission_id == RolePermission.permission_id
            )
            .where(
                UserRole.user_id == current_user.user_id,
                Permission.permission_code == permission_code,
            )
        )

        permission = db.scalar(statement)

        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_code}",
            )

        return current_user

    return permission_checker
