"""
Authentication endpoints: Login and Register.
Handles user authentication with JWT tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.security import security_manager
from app.core.config import settings
from app.api.dependencies import get_current_user
from app.core.jwt_blacklist import jwt_blacklist
from app.models.user import User, SubscriptionTier
from app.schemas.auth import (
    UserLoginRequest,
    UserRegisterRequest,
    UserOut,
    TokenResponse,
)
import logging
from datetime import datetime, timezone
from app.schemas.auth import RefreshTokenRequest
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        request: User registration data
        db: Database session

    Returns:
        Created user data

    Raises:
        HTTPException 400: Email already exists
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password
        password_hash = security_manager.hash_password(request.password)

        # Calculate quota reset date (next month)
        now = datetime.now(timezone.utc)
        if now.month == 12:
            reset_date = datetime(now.year + 1, 1, 1)
        else:
            reset_date = datetime(now.year, now.month + 1, 1)

        # Create new user
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
        # db.rollback() KALDIR - get_db dependency'si zaten yapıyor
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login user and return JWT tokens.

    Args:
        request: User login credentials
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException 401: Invalid credentials
    """
    try:
        # Find user by email
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
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
            )

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        # Create tokens
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Revoke the current access token by adding its jti to the Redis blacklist."""
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
async def refresh_token(request: RefreshTokenRequest):
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

    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = security_manager.create_access_token(
        data={"sub": subject},
        expires_delta=access_token_expires,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
    )
