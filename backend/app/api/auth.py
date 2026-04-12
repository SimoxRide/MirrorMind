"""Authentication & user management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Schemas ──────────────────────────────────────────────


class SetupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool
    email: str


class SetupStatusResponse(BaseModel):
    needs_setup: bool


class UserInfo(BaseModel):
    id: str
    email: str
    is_admin: bool


# ── Endpoints ────────────────────────────────────────────


@router.get("/setup-status", response_model=SetupStatusResponse)
async def check_setup_status(db: AsyncSession = Depends(get_db)):
    """Check if the system needs initial admin setup (first run detection)."""
    result = await db.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    return SetupStatusResponse(needs_setup=count == 0)


@router.post("/setup", response_model=TokenResponse)
async def initial_setup(data: SetupRequest, db: AsyncSession = Depends(get_db)):
    """First-run admin account creation. Only works when no users exist."""
    result = await db.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed. Use /auth/login instead.",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        is_admin=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "email": user.email, "admin": True}
    )
    return TokenResponse(access_token=token, is_admin=True, email=user.email)


@router.post("/register", response_model=TokenResponse)
async def register(data: SetupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new (non-admin) user."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        is_admin=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "email": user.email, "admin": False}
    )
    return TokenResponse(access_token=token, is_admin=False, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled.",
        )

    token = create_access_token(
        {"sub": str(user.id), "email": user.email, "admin": user.is_admin}
    )
    return TokenResponse(access_token=token, is_admin=user.is_admin, email=user.email)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(db: AsyncSession = Depends(get_db)):
    """Get current user info. Requires auth header (handled by middleware)."""
    # This will be populated by the auth middleware
    from app.core.deps import get_current_user

    # Placeholder — the actual dependency injection happens at the route level
    raise HTTPException(501, "Use the dependency-injected version")
