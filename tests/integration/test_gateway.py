"""Integration tests for the v1 HTTP API gateway."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.gateway import create_app


@pytest.fixture()
async def app_and_store(tmp_db_path, tmp_workspace):
    """Create a test app with in-memory store."""
    store = MemoryStore(tmp_db_path)
    await store.initialize()
    app = create_app(store=store, workspace=tmp_workspace)
    yield app, store
    await store.close()


@pytest.fixture()
async def client(app_and_store):
    app, _ = app_and_store
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
async def user_with_session(app_and_store):
    """Create a user and session, return (user_id, session_id)."""
    _, store = app_and_store
    user = await store.create_user(user_id="test-gw-user")
    session = await store.create_session("test-gw-user", title="Test Session")
    return user["user_id"], session["session_id"]


class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestUserEndpoints:
    async def test_create_user(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/users", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert "user_id" in data
        assert "created_at" in data

    async def test_create_user_with_id(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/users", json={"user_id": "my-custom-id"}
        )
        assert resp.status_code == 201
        assert resp.json()["user_id"] == "my-custom-id"

    async def test_create_duplicate_user(self, client: AsyncClient) -> None:
        await client.post("/api/v1/users", json={"user_id": "dup-user"})
        resp = await client.post(
            "/api/v1/users", json={"user_id": "dup-user"}
        )
        assert resp.status_code == 409


class TestSessionEndpoints:
    async def test_create_session(self, client: AsyncClient) -> None:
        user_resp = await client.post("/api/v1/users", json={})
        uid = user_resp.json()["user_id"]
        resp = await client.post(
            f"/api/v1/users/{uid}/sessions",
            json={"title": "My Chat"},
            headers={"X-User-Id": uid},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Chat"
        assert "session_id" in data

    async def test_list_sessions(self, client: AsyncClient) -> None:
        user_resp = await client.post("/api/v1/users", json={})
        uid = user_resp.json()["user_id"]
        await client.post(
            f"/api/v1/users/{uid}/sessions",
            json={"title": "Chat 1"},
            headers={"X-User-Id": uid},
        )
        await client.post(
            f"/api/v1/users/{uid}/sessions",
            json={"title": "Chat 2"},
            headers={"X-User-Id": uid},
        )
        resp = await client.get(
            f"/api/v1/users/{uid}/sessions",
            headers={"X-User-Id": uid},
        )
        assert resp.status_code == 200
        assert len(resp.json()["sessions"]) == 2

    async def test_delete_session(self, client: AsyncClient) -> None:
        user_resp = await client.post("/api/v1/users", json={})
        uid = user_resp.json()["user_id"]
        sess_resp = await client.post(
            f"/api/v1/users/{uid}/sessions",
            json={},
            headers={"X-User-Id": uid},
        )
        sid = sess_resp.json()["session_id"]
        resp = await client.delete(
            f"/api/v1/users/{uid}/sessions/{sid}",
            headers={"X-User-Id": uid},
        )
        assert resp.status_code == 204

    async def test_delete_session_wrong_user(
        self, client: AsyncClient
    ) -> None:
        u1 = (await client.post("/api/v1/users", json={"user_id": "u1"})).json()
        u2 = (await client.post("/api/v1/users", json={"user_id": "u2"})).json()
        sess = await client.post(
            f"/api/v1/users/u1/sessions",
            json={},
            headers={"X-User-Id": "u1"},
        )
        sid = sess.json()["session_id"]
        resp = await client.delete(
            f"/api/v1/users/u1/sessions/{sid}",
            headers={"X-User-Id": "u2"},
        )
        assert resp.status_code == 403


class TestMessageEndpoints:
    async def test_get_messages_empty(
        self, client: AsyncClient, user_with_session
    ) -> None:
        uid, sid = user_with_session
        resp = await client.get(
            f"/api/v1/users/{uid}/sessions/{sid}/messages",
            headers={"X-User-Id": uid},
        )
        assert resp.status_code == 200
        assert resp.json()["messages"] == []

    async def test_get_messages_with_limit(
        self, client: AsyncClient, user_with_session, app_and_store
    ) -> None:
        uid, sid = user_with_session
        _, store = app_and_store
        for i in range(5):
            await store.add_message(sid, uid, "user", f"msg {i}")
        resp = await client.get(
            f"/api/v1/users/{uid}/sessions/{sid}/messages?limit=2",
            headers={"X-User-Id": uid},
        )
        assert resp.status_code == 200
        assert len(resp.json()["messages"]) == 2


class TestOwnershipEnforcement:
    async def test_cross_user_session_access_forbidden(
        self, client: AsyncClient
    ) -> None:
        await client.post("/api/v1/users", json={"user_id": "owner"})
        await client.post("/api/v1/users", json={"user_id": "intruder"})
        sess = await client.post(
            "/api/v1/users/owner/sessions",
            json={},
            headers={"X-User-Id": "owner"},
        )
        sid = sess.json()["session_id"]
        # Intruder tries to list messages
        resp = await client.get(
            f"/api/v1/users/owner/sessions/{sid}/messages",
            headers={"X-User-Id": "intruder"},
        )
        assert resp.status_code == 403

    async def test_missing_user_id_header(
        self, client: AsyncClient
    ) -> None:
        await client.post("/api/v1/users", json={"user_id": "someone"})
        resp = await client.get("/api/v1/users/someone/sessions")
        assert resp.status_code == 422
