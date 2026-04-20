"""In-memory TTL cache for frequently accessed data."""

from cachetools import TTLCache

# Persona objects keyed by persona_id (str).  256 entries, 5 min TTL.
persona_cache: TTLCache = TTLCache(maxsize=256, ttl=300)


def invalidate_persona(persona_id) -> None:
    """Remove a single persona from the cache after mutation."""
    persona_cache.pop(str(persona_id), None)
