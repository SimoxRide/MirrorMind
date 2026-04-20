"""Rate limiting setup using slowapi.

A single :class:`Limiter` instance is exported; routes can use
``@limiter.limit(...)`` or the ``RateLimit`` helpers below. Limits are
disabled automatically when ``settings.rate_limit_enabled`` is False.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _key_func(request: Request) -> str:
    """Rate limit key — prefer authenticated user id, fall back to IP."""
    user = getattr(request.state, "user", None)
    if user is not None:
        user_id = getattr(user, "id", None)
        if user_id:
            return f"user:{user_id}"
    auth = request.headers.get("x-api-key")
    if auth:
        return f"apikey:{auth[:12]}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_key_func,
    enabled=get_settings().rate_limit_enabled,
    default_limits=[get_settings().rate_limit_default],
    headers_enabled=True,
)


def auth_limit() -> str:
    return get_settings().rate_limit_auth


def generate_limit() -> str:
    return get_settings().rate_limit_generate


def upload_limit() -> str:
    return get_settings().rate_limit_upload


def public_chat_limit() -> str:
    return get_settings().rate_limit_public_chat
