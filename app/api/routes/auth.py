
import hashlib
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.models.user import User, Role, UserRole
from app.models.refresh_token import RefreshToken
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    UserResponse,
    TokenResponse,
    MessageResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def store_refresh_token(db: Session, user_id: int, token: str):
    record = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        ),
    )

    db.add(record)


def create_token_pair(db: Session, user_id: int) -> TokenResponse:
    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(str(user_id))

    store_refresh_token(db, user_id, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token required",
            )

        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    user = db.get(User, user_id)

    if not user or user.account_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active",
        )

    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(
            (User.username == request.username)
            | (User.email == request.email)
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    learner_role = db.scalar(
        select(Role).where(Role.role_code == "LEARNER")
    )

    if not learner_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default learner role is not configured",
        )

    user = User(
        username=request.username,
        email=str(request.email),
        full_name=request.full_name,
        password_hash=hash_password(request.password),
        account_status="ACTIVE",
    )

    try:
        db.add(user)
        db.flush()

        db.add(
            UserRole(
                user_id=user.user_id,
                role_id=learner_role.role_id,
            )
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            (User.username == request.username_or_email)
            | (User.email == request.username_or_email)
        )
    )

    if (
        not user
        or not verify_password(request.password, user.password_hash)
        or user.account_status != "ACTIVE"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or inactive account",
        )

    try:
        user.last_login_at = datetime.utcnow()

        tokens = create_token_pair(db, user.user_id)

        db.commit()

        return tokens

    except Exception:
        db.rollback()
        raise


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        payload = decode_token(request.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required",
            )

        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    token_hash = hash_refresh_token(request.refresh_token)

    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )

    user = db.get(User, user_id)

    if not record or not user or user.account_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is revoked, expired or invalid",
        )

    try:
        record.revoked_at = datetime.utcnow()

        tokens = create_token_pair(db, user_id)

        db.commit()

        return tokens

    except Exception:
        db.rollback()
        raise


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(request.refresh_token)

    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == current_user.user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )

    if record:
        record.revoked_at = datetime.utcnow()
        db.commit()

    return MessageResponse(message="Logout successful")


@router.get("/me", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user
