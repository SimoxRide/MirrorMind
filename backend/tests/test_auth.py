"""Tests for authentication endpoints: setup, register, login, /me."""

import pytest
from httpx import AsyncClient

API = "/api/v1"


class TestAuthSetup:
    """First-run admin setup (/auth/setup)."""

    async def test_setup_creates_admin(self, client: AsyncClient):
        resp = await client.post(
            f"{API}/auth/setup",
            json={"email": "first@example.com", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_admin"] is True
        assert body["email"] == "first@example.com"
        assert "access_token" in body

    async def test_setup_fails_when_users_exist(self, client: AsyncClient, admin_user):
        """Setup should reject if any user already exists."""
        resp = await client.post(
            f"{API}/auth/setup",
            json={"email": "another@example.com", "password": "pass"},
        )
        assert resp.status_code == 400


class TestAuthRegister:
    async def test_register_creates_non_admin(self, client: AsyncClient, admin_user):
        """Register creates a normal user (after at least one admin exists)."""
        resp = await client.post(
            f"{API}/auth/register",
            json={"email": "new@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_admin"] is False
        assert body["email"] == "new@example.com"

    async def test_register_duplicate_email(self, client: AsyncClient, admin_user):
        await client.post(
            f"{API}/auth/register",
            json={"email": "dup@example.com", "password": "a"},
        )
        resp = await client.post(
            f"{API}/auth/register",
            json={"email": "dup@example.com", "password": "b"},
        )
        assert resp.status_code == 409


class TestAuthLogin:
    async def test_login_success(self, client: AsyncClient, admin_user):
        resp = await client.post(
            f"{API}/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["is_admin"] is True
        assert "access_token" in body

    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        resp = await client.post(
            f"{API}/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            f"{API}/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
        )
        assert resp.status_code == 401


class TestAuthMe:
    async def test_me_returns_user_info(self, client: AsyncClient, admin_headers):
        resp = await client.get(f"{API}/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "admin@example.com"
        assert body["is_admin"] is True

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get(f"{API}/auth/me")
        assert resp.status_code == 401
