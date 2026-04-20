"""Domain-specific exceptions for MirrorMind."""


class MirrorMindError(Exception):
    """Base exception for all MirrorMind domain errors."""

    def __init__(self, message: str = "", *, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class EntityNotFoundError(MirrorMindError):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, entity_id: str | None = None):
        detail = f"{entity} not found"
        if entity_id:
            detail = f"{entity} '{entity_id}' not found"
        super().__init__(detail, status_code=404)


class AccessDeniedError(MirrorMindError):
    """Raised when the current user lacks permission."""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(detail, status_code=403)


class LLMError(MirrorMindError):
    """Raised when an LLM agent call fails."""

    def __init__(self, agent_name: str = "unknown", cause: str = ""):
        detail = f"LLM agent '{agent_name}' failed"
        if cause:
            detail += f": {cause}"
        self.agent_name = agent_name
        super().__init__(detail, status_code=502)


class ProviderNotConfiguredError(MirrorMindError):
    """Raised when no LLM provider API key is available."""

    def __init__(self):
        super().__init__("Provider API key not configured", status_code=400)
