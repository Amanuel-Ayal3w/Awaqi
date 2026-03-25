"""Integration tests for admin endpoints (require PostgreSQL)."""

import uuid

import pytest

try:
    from tests.conftest import _HAS_DB
except ImportError:
    _HAS_DB = False

pytestmark = [
    pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not available"),
    pytest.mark.asyncio(loop_scope="session"),
]


class TestAdminDocuments:
    async def test_unauthenticated_returns_401(self, client):
        response = await client.get("/v1/admin/documents")
        assert response.status_code == 401

    async def test_authenticated_returns_documents(self, client, admin_session):
        response = await client.get(
            "/v1/admin/documents",
            headers={"Authorization": f"Bearer {admin_session.token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)


class TestAdminUsers:
    async def test_unauthenticated_returns_401(self, client):
        response = await client.get("/v1/admin/users")
        assert response.status_code == 401

    async def test_authenticated_returns_users(self, client, admin_session):
        response = await client.get(
            "/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_session.token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) >= 1  # at least the admin_user fixture


class TestDeleteUser:
    async def test_unauthenticated_returns_401(self, client):
        response = await client.delete(f"/v1/admin/users/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_editor_cannot_delete(self, client, editor_session):
        response = await client.delete(
            f"/v1/admin/users/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {editor_session.token}"},
        )
        assert response.status_code == 403

    async def test_cannot_delete_self(self, client, admin_session, admin_user):
        response = await client.delete(
            f"/v1/admin/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_session.token}"},
        )
        assert response.status_code == 400
        assert "own account" in response.json()["detail"]

    async def test_delete_nonexistent_returns_404(self, client, admin_session):
        response = await client.delete(
            f"/v1/admin/users/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_session.token}"},
        )
        assert response.status_code == 404

    async def test_superadmin_can_delete_editor(
        self, client, admin_session, editor_user
    ):
        response = await client.delete(
            f"/v1/admin/users/{editor_user.id}",
            headers={"Authorization": f"Bearer {admin_session.token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAdminLogs:
    async def test_unauthenticated_returns_401(self, client):
        response = await client.get("/v1/admin/logs")
        assert response.status_code == 401

    async def test_authenticated_returns_logs(self, client, admin_session):
        response = await client.get(
            "/v1/admin/logs",
            headers={"Authorization": f"Bearer {admin_session.token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) >= 1  # at least the "no messages" fallback


class TestAdminUpload:
    async def test_unauthenticated_returns_401(self, client):
        response = await client.post("/v1/admin/upload")
        assert response.status_code == 401

    async def test_editor_cannot_upload(self, client, editor_session):
        response = await client.post(
            "/v1/admin/upload",
            headers={"Authorization": f"Bearer {editor_session.token}"},
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert response.status_code == 403

    async def test_non_pdf_rejected(self, client, admin_session):
        response = await client.post(
            "/v1/admin/upload",
            headers={"Authorization": f"Bearer {admin_session.token}"},
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 415
