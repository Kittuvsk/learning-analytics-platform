
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    refresh_token_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=False
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_refresh_tokens_user_expiry", "user_id", "expires_at"),
    )
