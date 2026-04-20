"""CloneEngine tests — mock the OpenAI Agents Runner, exercise the pipeline."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import Memory, PersonaCore
from app.models.policy import PolicyRule
from app.models.user import User
from app.schemas.core import CloneRequest, CloneResponse
from app.services.clone_engine import CloneEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _make_persona(owner: User, *, name: str = "TestClone") -> PersonaCore:
    return PersonaCore(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name=name,
        identity_summary="A friendly tester persona.",
        autonomy_level="medium",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_memory(persona: PersonaCore, title: str = "Mem") -> Memory:
    return Memory(
        id=uuid.uuid4(),
        persona_id=persona.id,
        memory_type="long_term",
        title=title,
        content="Some memory content.",
        source="test",
        confidence=0.9,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _fake_runner_result(output: str | dict) -> MagicMock:
    """Simulate agents.Runner.run() result."""
    result = MagicMock()
    result.final_output = json.dumps(output) if isinstance(output, dict) else output
    return result


def _mock_graph_retriever():
    """Return a mock GraphRetriever class whose instances have async methods."""
    mock_cls = MagicMock()
    instance = MagicMock()
    instance.retrieve_for_context = AsyncMock(return_value="")
    mock_cls.return_value = instance
    return mock_cls


_GR_PATCH = "app.services.clone_engine.GraphRetriever"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCloneEngineGenerate:
    async def test_no_api_key_returns_placeholder(
        self, db: AsyncSession, regular_user: User
    ):
        """Without a configured provider, generate returns a fallback message."""
        persona = _make_persona(regular_user)
        db.add(persona)
        await db.flush()

        with (
            patch(_GR_PATCH, _mock_graph_retriever()),
            patch("app.services.clone_engine.resolve_provider_settings") as mock_ps,
        ):
            ps = MagicMock()
            ps.configured = False
            mock_ps.return_value = ps

            engine = CloneEngine(db)
            req = CloneRequest(
                persona_id=persona.id,
                message="Hello!",
            )
            resp = await engine.generate(req, user=None)

        assert isinstance(resp, CloneResponse)
        assert resp.confidence == 0.0
        assert (
            "configured" in resp.response.lower() or "provider" in resp.response.lower()
        )

    async def test_persona_not_found(self, db: AsyncSession, regular_user: User):
        with patch(_GR_PATCH, _mock_graph_retriever()):
            engine = CloneEngine(db)
            req = CloneRequest(
                persona_id=uuid.uuid4(),
                message="Hello!",
            )
            with patch(
                "app.services.clone_engine.resolve_provider_settings"
            ) as mock_settings:
                ps = MagicMock()
                ps.configured = True
                mock_settings.return_value = ps

                resp = await engine.generate(req, user=regular_user)
        assert resp.confidence == 0.0
        assert "not found" in resp.response.lower()

    async def test_full_pipeline_with_mock_runner(
        self, db: AsyncSession, regular_user: User
    ):
        """Mock Runner.run for both generator and critic — verify full pipeline output."""
        persona = _make_persona(regular_user)
        db.add(persona)
        mem = _make_memory(persona, "Childhood")
        db.add(mem)
        pol = PolicyRule(
            id=uuid.uuid4(),
            persona_id=persona.id,
            policy_type="tone",
            name="Be gentle",
            description="Always be gentle.",
            created_at=_NOW,
            updated_at=_NOW,
        )
        db.add(pol)
        await db.flush()

        gen_output = {
            "response": "Hey there! How can I help?",
            "confidence": 0.85,
            "requires_review": False,
            "reasoning": "Friendly greeting",
        }
        critic_output = {
            "approved": True,
            "issues": [],
            "scores": {"tone": 0.9, "accuracy": 0.8},
        }

        fake_gen = _fake_runner_result(gen_output)
        fake_critic = _fake_runner_result(critic_output)

        with (
            patch("app.services.clone_engine.resolve_provider_settings") as mock_ps,
            patch("app.services.clone_engine.Runner") as MockRunner,
            patch(_GR_PATCH, _mock_graph_retriever()),
        ):
            ps = MagicMock()
            ps.configured = True
            ps.to_run_config.return_value = {}
            mock_ps.return_value = ps

            MockRunner.run = AsyncMock(side_effect=[fake_gen, fake_critic])

            engine = CloneEngine(db)
            req = CloneRequest(persona_id=persona.id, message="Ciao!")
            resp = await engine.generate(req, user=regular_user)

        assert resp.response == "Hey there! How can I help?"
        assert resp.confidence == 0.85
        assert resp.requires_review is False
        assert resp.trace["persona_name"] == persona.name
        assert resp.trace["memories_count"] >= 1
        assert resp.trace["policies_count"] >= 1

    async def test_critic_rejection_uses_suggested_edit(
        self, db: AsyncSession, regular_user: User
    ):
        persona = _make_persona(regular_user)
        db.add(persona)
        await db.flush()

        gen_output = {
            "response": "Yo dawg, sup!",
            "confidence": 0.7,
            "requires_review": False,
        }
        critic_output = {
            "approved": False,
            "issues": ["Too informal"],
            "scores": {"tone": 0.3},
            "suggested_edit": "Hello! How are you today?",
        }

        with (
            patch("app.services.clone_engine.resolve_provider_settings") as mock_ps,
            patch("app.services.clone_engine.Runner") as MockRunner,
            patch(_GR_PATCH, _mock_graph_retriever()),
        ):
            ps = MagicMock()
            ps.configured = True
            ps.to_run_config.return_value = {}
            mock_ps.return_value = ps

            MockRunner.run = AsyncMock(
                side_effect=[
                    _fake_runner_result(gen_output),
                    _fake_runner_result(critic_output),
                ]
            )

            engine = CloneEngine(db)
            req = CloneRequest(persona_id=persona.id, message="Hi!")
            resp = await engine.generate(req, user=regular_user)

        assert resp.response == "Hello! How are you today?"
        assert resp.requires_review is True
        assert resp.trace.get("used_critic_edit") is True
