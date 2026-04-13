"""Resolve effective provider settings with user override precedence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import Settings, get_settings
from app.models.user import User

if TYPE_CHECKING:
    from agents import RunConfig


@dataclass(slots=True)
class EffectiveProviderSettings:
    api_key: str = ""
    api_base: str = ""
    model: str = ""
    source: str = "none"
    has_user_api_key: bool = False
    has_env_api_key: bool = False
    user_api_base: str | None = None
    user_model: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def effective_api_base(self) -> str:
        return self.api_base or "https://api.openai.com/v1 (default)"

    def to_run_config(self) -> RunConfig | None:
        if not self.configured:
            return None
        from agents import OpenAIProvider, RunConfig

        provider = OpenAIProvider(
            api_key=self.api_key,
            base_url=self.api_base or None,
        )
        return RunConfig(model=self.model, model_provider=provider)


def resolve_provider_settings(
    user: User | None,
    settings: Settings | None = None,
) -> EffectiveProviderSettings:
    settings = settings or get_settings()

    user_api_key = _clean_secret(getattr(user, "provider_api_key", None))
    user_api_base = _clean_optional(getattr(user, "provider_api_base", None))
    user_model = _clean_optional(getattr(user, "provider_model", None))
    env_api_key = _clean_secret(settings.openai_api_key)
    env_api_base = _clean_optional(settings.openai_api_base)
    env_model = _clean_optional(settings.openai_model) or "gpt-4o"

    return EffectiveProviderSettings(
        api_key=user_api_key or env_api_key or "",
        api_base=user_api_base or env_api_base or "",
        model=user_model or env_model,
        source="user" if user_api_key else ("env" if env_api_key else "none"),
        has_user_api_key=bool(user_api_key),
        has_env_api_key=bool(env_api_key),
        user_api_base=user_api_base,
        user_model=user_model,
    )


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_secret(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
