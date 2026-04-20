"""CRUD tests for Personas, Memories, and Policies API endpoints."""

import uuid

import pytest
from httpx import AsyncClient

API = "/api/v1"


# ═══════════════════════════════════════════════════════════
#  Persona CRUD
# ═══════════════════════════════════════════════════════════


class TestPersonaCRUD:
    async def test_create_persona(self, client: AsyncClient, user_headers):
        resp = await client.post(
            f"{API}/personas/",
            json={"name": "Test Clone", "identity_summary": "A test persona"},
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Clone"
        assert data["identity_summary"] == "A test persona"
        assert data["autonomy_level"] == "medium"

    async def test_create_persona_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            f"{API}/personas/",
            json={"name": "No Auth"},
        )
        assert resp.status_code == 401

    async def test_list_personas_own(
        self, client: AsyncClient, user_headers, admin_headers
    ):
        """Regular user sees only their own personas."""
        # Admin creates one
        r1 = await client.post(
            f"{API}/personas/",
            json={"name": "Admin Persona"},
            headers=admin_headers,
        )
        assert r1.status_code == 201

        # User creates one
        r2 = await client.post(
            f"{API}/personas/",
            json={"name": "User Persona"},
            headers=user_headers,
        )
        assert r2.status_code == 201

        # User list — sees their own + ownerless (legacy), NOT admin's
        resp = await client.get(f"{API}/personas/", headers=user_headers)
        assert resp.status_code == 200
        names = {p["name"] for p in resp.json()}
        assert "User Persona" in names

    async def test_admin_sees_all_personas(
        self, client: AsyncClient, admin_headers, user_headers
    ):
        await client.post(
            f"{API}/personas/",
            json={"name": "AdminP"},
            headers=admin_headers,
        )
        await client.post(
            f"{API}/personas/",
            json={"name": "UserP"},
            headers=user_headers,
        )
        resp = await client.get(f"{API}/personas/", headers=admin_headers)
        assert resp.status_code == 200
        names = {p["name"] for p in resp.json()}
        assert "AdminP" in names
        assert "UserP" in names

    async def test_get_persona_forbidden(
        self, client: AsyncClient, user_headers, other_headers
    ):
        """User cannot access another user's persona."""
        r = await client.post(
            f"{API}/personas/",
            json={"name": "Owned"},
            headers=user_headers,
        )
        pid = r.json()["id"]

        resp = await client.get(f"{API}/personas/{pid}", headers=other_headers)
        assert resp.status_code == 403

    async def test_patch_persona(self, client: AsyncClient, user_headers):
        r = await client.post(
            f"{API}/personas/",
            json={"name": "Before"},
            headers=user_headers,
        )
        pid = r.json()["id"]
        resp = await client.patch(
            f"{API}/personas/{pid}",
            json={"name": "After", "autonomy_level": "high"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"
        assert resp.json()["autonomy_level"] == "high"

    async def test_delete_persona(self, client: AsyncClient, user_headers):
        r = await client.post(
            f"{API}/personas/",
            json={"name": "ToDelete"},
            headers=user_headers,
        )
        pid = r.json()["id"]
        resp = await client.delete(f"{API}/personas/{pid}", headers=user_headers)
        assert resp.status_code == 204

        # Soft delete — persona still visible but is_active=False
        resp2 = await client.get(f"{API}/personas/{pid}", headers=user_headers)
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is False

    async def test_create_persona_invalid_autonomy(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.post(
            f"{API}/personas/",
            json={"name": "Bad", "autonomy_level": "super"},
            headers=user_headers,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════
#  Memory CRUD
# ═══════════════════════════════════════════════════════════


class TestMemoryCRUD:
    @pytest.fixture
    async def persona_id(self, client: AsyncClient, user_headers) -> str:
        r = await client.post(
            f"{API}/personas/",
            json={"name": "MemPersona"},
            headers=user_headers,
        )
        return r.json()["id"]

    async def test_create_memory(self, client, user_headers, persona_id):
        resp = await client.post(
            f"{API}/memories/",
            json={
                "persona_id": persona_id,
                "memory_type": "long_term",
                "title": "Childhood",
                "content": "Grew up in Rome",
            },
            headers=user_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Childhood"

    async def test_create_memory_invalid_type(self, client, user_headers, persona_id):
        resp = await client.post(
            f"{API}/memories/",
            json={
                "persona_id": persona_id,
                "memory_type": "invalid_type",
                "title": "Bad",
                "content": "Should fail",
            },
            headers=user_headers,
        )
        assert resp.status_code == 422

    async def test_list_memories(self, client, user_headers, persona_id):
        for i in range(3):
            await client.post(
                f"{API}/memories/",
                json={
                    "persona_id": persona_id,
                    "memory_type": "episodic",
                    "title": f"Memory {i}",
                    "content": f"Content {i}",
                },
                headers=user_headers,
            )
        resp = await client.get(
            f"{API}/memories/",
            params={"persona_id": persona_id},
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    async def test_memory_cross_user_forbidden(
        self, client, user_headers, other_headers, persona_id
    ):
        """Other user cannot list memories for a persona they don't own."""
        resp = await client.get(
            f"{API}/memories/",
            params={"persona_id": persona_id},
            headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_update_memory(self, client, user_headers, persona_id):
        r = await client.post(
            f"{API}/memories/",
            json={
                "persona_id": persona_id,
                "memory_type": "preference",
                "title": "Coffee",
                "content": "Likes espresso",
            },
            headers=user_headers,
        )
        mid = r.json()["id"]
        resp = await client.patch(
            f"{API}/memories/{mid}",
            json={"content": "Loves espresso doppio"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Loves espresso doppio"

    async def test_delete_memory(self, client, user_headers, persona_id):
        r = await client.post(
            f"{API}/memories/",
            json={
                "persona_id": persona_id,
                "memory_type": "relational",
                "title": "Friend",
                "content": "Best friend Marco",
            },
            headers=user_headers,
        )
        mid = r.json()["id"]
        resp = await client.delete(f"{API}/memories/{mid}", headers=user_headers)
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════
#  Policy CRUD
# ═══════════════════════════════════════════════════════════


class TestPolicyCRUD:
    @pytest.fixture
    async def persona_id(self, client: AsyncClient, user_headers) -> str:
        r = await client.post(
            f"{API}/personas/",
            json={"name": "PolPersona"},
            headers=user_headers,
        )
        return r.json()["id"]

    async def test_create_policy(self, client, user_headers, persona_id):
        resp = await client.post(
            f"{API}/policies/",
            json={
                "persona_id": persona_id,
                "policy_type": "tone",
                "name": "Stay calm",
                "description": "Always respond calmly",
            },
            headers=user_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Stay calm"

    async def test_list_policies_filter_type(self, client, user_headers, persona_id):
        await client.post(
            f"{API}/policies/",
            json={
                "persona_id": persona_id,
                "policy_type": "tone",
                "name": "P1",
            },
            headers=user_headers,
        )
        await client.post(
            f"{API}/policies/",
            json={
                "persona_id": persona_id,
                "policy_type": "escalation",
                "name": "P2",
            },
            headers=user_headers,
        )
        resp = await client.get(
            f"{API}/policies/",
            params={"persona_id": persona_id, "policy_type": "tone"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert all(p["policy_type"] == "tone" for p in resp.json())

    async def test_update_policy_version_increments(
        self, client, user_headers, persona_id
    ):
        r = await client.post(
            f"{API}/policies/",
            json={
                "persona_id": persona_id,
                "policy_type": "risk_tolerance",
                "name": "Cautious",
            },
            headers=user_headers,
        )
        pid = r.json()["id"]
        v1 = r.json()["version"]

        resp = await client.patch(
            f"{API}/policies/{pid}",
            json={"description": "Updated desc"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == v1 + 1

    async def test_delete_policy(self, client, user_headers, persona_id):
        r = await client.post(
            f"{API}/policies/",
            json={
                "persona_id": persona_id,
                "policy_type": "forbidden_pattern",
                "name": "No slang",
            },
            headers=user_headers,
        )
        pid = r.json()["id"]
        resp = await client.delete(f"{API}/policies/{pid}", headers=user_headers)
        assert resp.status_code == 204

    async def test_policy_cross_user_forbidden(
        self, client, user_headers, other_headers, persona_id
    ):
        resp = await client.get(
            f"{API}/policies/",
            params={"persona_id": persona_id},
            headers=other_headers,
        )
        assert resp.status_code == 403
