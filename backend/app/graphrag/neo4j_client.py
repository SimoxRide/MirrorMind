"""Neo4j async client wrapper with circuit breaker."""

import time
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("neo4j_client")

_driver: AsyncDriver | None = None

# ---------------------------------------------------------------------------
# Simple circuit breaker
# ---------------------------------------------------------------------------

_CB_THRESHOLD = 3  # failures before opening
_CB_RECOVERY_TIMEOUT = 30  # seconds before trying again

_cb_failures: int = 0
_cb_open_since: float = 0.0


def _cb_is_open() -> bool:
    global _cb_failures, _cb_open_since
    if _cb_failures >= _CB_THRESHOLD:
        if time.monotonic() - _cb_open_since < _CB_RECOVERY_TIMEOUT:
            return True
        # Half-open: allow one attempt
        _cb_failures = _CB_THRESHOLD - 1
    return False


def _cb_record_success() -> None:
    global _cb_failures, _cb_open_since
    _cb_failures = 0
    _cb_open_since = 0.0


def _cb_record_failure() -> None:
    global _cb_failures, _cb_open_since
    _cb_failures += 1
    if _cb_failures >= _CB_THRESHOLD:
        _cb_open_since = time.monotonic()
        logger.warning("neo4j_circuit_open", failures=_cb_failures)


class Neo4jClient:
    """Thin async wrapper around the Neo4j Python driver."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def verify_connectivity(self) -> bool:
        try:
            await self._driver.verify_connectivity()
            _cb_record_success()
            return True
        except Exception:
            _cb_record_failure()
            logger.exception("neo4j_connectivity_check_failed")
            return False

    @asynccontextmanager
    async def session(self):
        async with self._driver.session() as s:
            yield s

    async def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if _cb_is_open():
            logger.warning("neo4j_circuit_open_skip_query")
            return []
        try:
            async with self.session() as s:
                result = await s.run(query, params or {})
                records = await result.data()
            _cb_record_success()
            return records
        except Exception:
            _cb_record_failure()
            logger.exception("neo4j_query_failed", query=query[:120])
            return []

    async def close(self) -> None:
        await self._driver.close()


def get_neo4j_client() -> Neo4jClient:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return Neo4jClient(_driver)


async def close_neo4j() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
