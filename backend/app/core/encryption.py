"""Symmetric encryption helpers (Fernet) for secrets at rest.

Used to encrypt sensitive credentials (bot tokens, API keys) stored in the
database. Keys are read from ``settings.encryption_key``. If not set, a key
derived from ``secret_key`` is used — acceptable for development but
**strongly discouraged** in production. Set ``ENCRYPTION_KEY`` explicitly.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_ENC_MARK = "_enc"  # marker key in credentials dicts indicating encrypted payload


@lru_cache
def _get_fernet() -> Fernet:
    settings = get_settings()
    raw = (settings.encryption_key or "").strip()
    if raw:
        try:
            return Fernet(raw.encode() if isinstance(raw, str) else raw)
        except Exception as exc:  # invalid encoded key
            raise RuntimeError(
                "ENCRYPTION_KEY is not a valid urlsafe base64 Fernet key"
            ) from exc
    if settings.is_production():
        raise RuntimeError(
            "ENCRYPTION_KEY must be set in production. Generate with "
            "`python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`."
        )
    # Development-only fallback derived from secret_key.
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    derived = base64.urlsafe_b64encode(digest)
    return Fernet(derived)


def encrypt_str(value: str) -> str:
    return _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_str(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - misuse
        raise ValueError("Invalid or corrupted encrypted value") from exc


# ── Credentials dict helpers ─────────────────────────────
# Credentials are stored in JSONB. We transparently encrypt them by keeping
# the shape ``{"_enc": "<fernet token>"}`` on disk and decoding on read.


def encrypt_credentials(data: dict | None) -> dict | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise TypeError("credentials must be a dict")
    if _ENC_MARK in data and len(data) == 1:
        # Already encrypted envelope — keep as-is.
        return data
    import json

    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return {_ENC_MARK: encrypt_str(payload)}


def decrypt_credentials(data: dict | None) -> dict | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        return data  # unexpected shape, return as-is
    if _ENC_MARK not in data:
        # Legacy unencrypted record — return as-is so migrations are transparent.
        return data
    import json

    token = data.get(_ENC_MARK)
    if not isinstance(token, str):
        return data
    try:
        return json.loads(decrypt_str(token))
    except Exception:  # pragma: no cover - corrupted data
        return {}


def is_encrypted(data: Any) -> bool:
    return isinstance(data, dict) and _ENC_MARK in data
