
from sqlalchemy import (
    BigInteger,
    String,
    Enum,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    full_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    account_status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "INACTIVE", "LOCKED", "PENDING"),
        nullable=False,
        default="PENDING"
    )

    last_login_at: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    updated_at = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    user_roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    role_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )

    role_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    user_roles = relationship("UserRole", back_populates="role")
    role_permissions = relationship(
        "RolePermission", back_populates="role"
    )


class Permission(Base):
    __tablename__ = "permissions"

    permission_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    permission_code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    role_permissions = relationship(
        "RolePermission", back_populates="permission"
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        primary_key=True
    )

    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.role_id"),
        primary_key=True
    )

    assigned_at = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.role_id"),
        primary_key=True
    )

    permission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("permissions.permission_id"),
        primary_key=True
    )

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship(
        "Permission", back_populates="role_permissions"
    )
