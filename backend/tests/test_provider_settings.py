from types import SimpleNamespace

from app.core.config import Settings
from app.services.provider_settings import resolve_provider_settings


def test_user_provider_settings_take_precedence_over_env():
    user = SimpleNamespace(
        provider_api_key="user-key",
        provider_api_base="https://user.example/v1",
        provider_model="user-model",
    )
    settings = Settings(
        openai_api_key="env-key",
        openai_api_base="https://env.example/v1",
        openai_model="env-model",
    )

    resolved = resolve_provider_settings(user, settings)

    assert resolved.configured is True
    assert resolved.source == "user"
    assert resolved.api_key == "user-key"
    assert resolved.api_base == "https://user.example/v1"
    assert resolved.model == "user-model"
    assert resolved.has_user_api_key is True
    assert resolved.has_env_api_key is True


def test_env_provider_settings_are_used_when_user_has_no_override():
    user = SimpleNamespace(
        provider_api_key=None,
        provider_api_base=None,
        provider_model=None,
    )
    settings = Settings(
        openai_api_key="env-key",
        openai_api_base="https://env.example/v1",
        openai_model="env-model",
    )

    resolved = resolve_provider_settings(user, settings)

    assert resolved.source == "env"
    assert resolved.api_key == "env-key"
    assert resolved.api_base == "https://env.example/v1"
    assert resolved.model == "env-model"
    assert resolved.has_user_api_key is False


def test_missing_user_key_still_allows_user_base_and_model_override():
    user = SimpleNamespace(
        provider_api_key=None,
        provider_api_base="https://user.example/v1",
        provider_model="user-model",
    )
    settings = Settings(
        openai_api_key="env-key",
        openai_api_base="https://env.example/v1",
        openai_model="env-model",
    )

    resolved = resolve_provider_settings(user, settings)

    assert resolved.source == "env"
    assert resolved.api_key == "env-key"
    assert resolved.api_base == "https://user.example/v1"
    assert resolved.model == "user-model"
