"""Neo4j async client wrapper."""

from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("neo4j_client")

_driver: AsyncDriver | None = None


class Neo4jClient:
    """Thin async wrapper around the Neo4j Python driver."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def verify_connectivity(self) -> bool:
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            logger.exception("neo4j_connectivity_check_failed")
            return False

    @asynccontextmanager
    async def session(self):
        async with self._driver.session() as s:
            yield s

    async def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self.session() as s:
            result = await s.run(query, params or {})
            records = await result.data()
            return records

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
