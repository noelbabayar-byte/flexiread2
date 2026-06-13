"""
Authentication endpoints: Login, Register, Logout, Refresh.
Handles user authentication with JWT tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from uuid import UUID
from app.core.database import get_db
from app.core.security import security_manager
from app.core.config import settings
from app.api.dependencies import get_current_user, security
from app.core.jwt_blacklist import jwt_blacklist
from app.models.user import User, SubscriptionTier
from app.schemas.auth import (
    UserLoginRequest,
    UserRegisterRequest,
    UserOut,
    TokenResponse,
    RefreshTokenRequest,
)
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        password_hash = security_manager.hash_password(request.password)

        now = datetime.now(timezone.utc)
        if now.month == 12:
            reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

        user = User(
            email=request.email,
            password_hash=password_hash,
            full_name=request.full_name,
            plan_type=SubscriptionTier.FREE,
            ocr_quota_remaining=settings.FREE_TIER_MONTHLY_QUOTA,
            ocr_quota_reset_date=reset_date,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User registered successfully: {user.email}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT tokens."""
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user or not security_manager.verify_password(
            request.password, user.password_hash
        ):
            logger.warning(f"Failed login attempt: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        user.last_login = datetime.now(timezone.utc)
        db.commit()

        access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        access_token = security_manager.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        refresh_token = security_manager.create_refresh_token(
            data={"sub": str(user.id)}
        )

        logger.info(f"User logged in successfully: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Revoke the current access token."""
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        jwt_blacklist.blacklist_token(
            jti,
            datetime.fromtimestamp(exp, tz=timezone.utc),
        )

    logger.info("User logged out successfully: %s", current_user.email)
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = security_manager.verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(subject)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    old_jti = payload.get("jti")
    old_exp = payload.get("exp")
    if old_jti and old_exp:
        jwt_blacklist.blacklist_token(
            old_jti, datetime.fromtimestamp(old_exp, tz=timezone.utc)
        )

    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = security_manager.create_access_token(
        data={"sub": subject},
        expires_delta=access_token_expires,
    )
    new_refresh_token = security_manager.create_refresh_token(data={"sub": subject})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
    )
