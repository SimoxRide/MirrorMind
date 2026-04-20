"""Authentication, user info, and per-user provider settings routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import auth_limit, limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.services.provider_settings import resolve_provider_settings

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


class ProviderSettingsResponse(BaseModel):
    has_user_api_key: bool
    api_key_source: str
    effective_api_base: str
    effective_model: str
    user_api_base: str | None = None
    user_model: str | None = None


class ProviderSettingsUpdate(BaseModel):
    api_key: str | None = None
    api_base: str | None = None
    model: str | None = None


# ── Endpoints ────────────────────────────────────────────


@router.get("/setup-status", response_model=SetupStatusResponse)
async def check_setup_status(db: AsyncSession = Depends(get_db)):
    """Check if the system needs initial admin setup (first run detection)."""
    result = await db.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    return SetupStatusResponse(needs_setup=count == 0)


@router.post("/setup", response_model=TokenResponse)
@limiter.limit(auth_limit())
async def initial_setup(
    request: Request,
    data: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
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
@limiter.limit(auth_limit())
async def register(
    request: Request,
    data: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
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
@limiter.limit(auth_limit())
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
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
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get the authenticated user's basic profile."""
    return UserInfo(id=str(user.id), email=user.email, is_admin=user.is_admin)


@router.get("/provider-settings", response_model=ProviderSettingsResponse)
async def get_provider_settings(user: User = Depends(get_current_user)):
    """Return effective provider settings with user-overrides-first precedence."""
    resolved = resolve_provider_settings(user)
    return ProviderSettingsResponse(
        has_user_api_key=resolved.has_user_api_key,
        api_key_source=resolved.source,
        effective_api_base=resolved.effective_api_base,
        effective_model=resolved.model,
        user_api_base=resolved.user_api_base,
        user_model=resolved.user_model,
    )


@router.patch("/provider-settings", response_model=ProviderSettingsResponse)
async def update_provider_settings(
    data: ProviderSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update per-user provider settings used before falling back to .env."""
    updated_fields = data.model_fields_set

    if "api_key" in updated_fields:
        user.provider_api_key = _normalize_provider_field(data.api_key)
    if "api_base" in updated_fields:
        user.provider_api_base = _normalize_provider_field(data.api_base)
    if "model" in updated_fields:
        user.provider_model = _normalize_provider_field(data.model)

    await db.flush()
    await db.refresh(user)

    resolved = resolve_provider_settings(user)
    return ProviderSettingsResponse(
        has_user_api_key=resolved.has_user_api_key,
        api_key_source=resolved.source,
        effective_api_base=resolved.effective_api_base,
        effective_model=resolved.model,
        user_api_base=resolved.user_api_base,
        user_model=resolved.user_model,
    )


def _normalize_provider_field(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
