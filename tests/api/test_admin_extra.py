"""
Integration tests for admin routes not covered by test_admin_endpoints.py:
  - GET  /v1/admin/analytics
  - GET  /v1/admin/system-health
  - GET  /v1/admin/vector-store
  - DELETE /v1/admin/vector-store/embeddings (superadmin)
  - GET  /v1/admin/documents/{doc_id}          (detail + error cases)
  - PATCH /v1/admin/documents/{doc_id}         (superadmin only)
  - POST  /v1/admin/documents/{doc_id}/ingest-text
  - PATCH /v1/admin/users/{user_id}
  - POST  /v1/admin/scrape
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

try:
    from tests.conftest import _HAS_DB
except ImportError:
    _HAS_DB = False

pytestmark = [
    pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not available"),
    pytest.mark.asyncio(loop_scope="session"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(session) -> dict:
    return {"Authorization": f"Bearer {session.token}"}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class TestAdminAnalytics:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/v1/admin/analytics")
        assert resp.status_code == 401

    async def test_editor_can_access_analytics(self, client, editor_session):
        resp = await client.get("/v1/admin/analytics", headers=_auth(editor_session))
        assert resp.status_code == 200

    async def test_analytics_has_required_fields(self, client, admin_session):
        resp = await client.get("/v1/admin/analytics", headers=_auth(admin_session))
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "documents_total",
            "documents_by_status",
            "chunks_total",
            "admin_users_total",
            "customer_users_total",
            "chat_sessions_total",
            "messages_total",
            "messages_last_7_days",
        ):
            assert field in data, f"missing field: {field}"

    async def test_analytics_counts_are_non_negative(self, client, admin_session):
        resp = await client.get("/v1/admin/analytics", headers=_auth(admin_session))
        data = resp.json()
        for field in ("documents_total", "chunks_total", "admin_users_total"):
            assert data[field] >= 0


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------

class TestAdminSystemHealth:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/v1/admin/system-health")
        assert resp.status_code == 401

    async def test_returns_200_with_db_status(self, client, admin_session):
        resp = await client.get("/v1/admin/system-health", headers=_auth(admin_session))
        assert resp.status_code == 200
        data = resp.json()
        assert "database_ok" in data
        assert "redis_ok" in data
        assert data["database_ok"] is True

    async def test_editor_can_access_system_health(self, client, editor_session):
        resp = await client.get("/v1/admin/system-health", headers=_auth(editor_session))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

class TestAdminVectorStore:
    async def test_unauthenticated_stats_returns_401(self, client):
        resp = await client.get("/v1/admin/vector-store")
        assert resp.status_code == 401

    async def test_stats_returns_200(self, client, admin_session):
        resp = await client.get("/v1/admin/vector-store", headers=_auth(admin_session))
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "configured_dimension",
            "embedding_model",
            "chunks_total",
            "chunks_with_embedding",
            "storage_bytes",
            "dimension_mismatch",
        ):
            assert field in data

    async def test_wipe_embeddings_requires_superadmin(self, client, editor_session):
        resp = await client.delete(
            "/v1/admin/vector-store/embeddings",
            headers=_auth(editor_session),
        )
        assert resp.status_code == 403

    async def test_wipe_embeddings_superadmin(self, client, admin_session, db_session):
        from database.models.document import Document, DocumentChunk, DocumentStatus as DocStatusEnum

        doc = Document(
            title="vec-test",
            status=DocStatusEnum.INDEXED,
            source_type="upload",
        )
        db_session.add(doc)
        await db_session.flush()
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="hello",
            embedding=[0.1] * 1536,
        )
        db_session.add(chunk)
        await db_session.commit()

        resp = await client.delete(
            "/v1/admin/vector-store/embeddings",
            headers=_auth(admin_session),
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "wipe_embeddings"
        assert resp.json()["affected_rows"] >= 1


# ---------------------------------------------------------------------------
# Document detail
# ---------------------------------------------------------------------------

class TestAdminDocumentDetail:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get(f"/v1/admin/documents/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_nonexistent_returns_404(self, client, admin_session):
        resp = await client.get(
            f"/v1/admin/documents/{uuid.uuid4()}",
            headers=_auth(admin_session),
        )
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_400(self, client, admin_session):
        resp = await client.get(
            "/v1/admin/documents/not-a-uuid",
            headers=_auth(admin_session),
        )
        assert resp.status_code == 400

    async def test_existing_document_returns_detail(self, client, admin_session, db_session):
        from database.models.document import Document, DocumentStatus as DocStatusEnum

        doc = Document(
            id=uuid.uuid4(),
            title="Test Detail Doc",
            file_hash="detailhash123",
            status=DocStatusEnum.PENDING,
            uploaded_by_id=None,
        )
        db_session.add(doc)
        await db_session.commit()

        resp = await client.get(
            f"/v1/admin/documents/{doc.id}",
            headers=_auth(admin_session),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(doc.id)
        assert data["title"] == "Test Detail Doc"
        assert "file_hash" in data


# ---------------------------------------------------------------------------
# Document patch
# ---------------------------------------------------------------------------

class TestPatchAdminDocument:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.patch(f"/v1/admin/documents/{uuid.uuid4()}", json={})
        assert resp.status_code == 401

    async def test_editor_cannot_patch_document(self, client, editor_session):
        resp = await client.patch(
            f"/v1/admin/documents/{uuid.uuid4()}",
            json={},
            headers=_auth(editor_session),
        )
        assert resp.status_code == 403

    async def test_nonexistent_returns_404(self, client, admin_session):
        resp = await client.patch(
            f"/v1/admin/documents/{uuid.uuid4()}",
            json={"uploaded_by_id": None},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_400(self, client, admin_session):
        resp = await client.patch(
            "/v1/admin/documents/bad-uuid",
            json={},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 400

    async def test_superadmin_can_clear_uploader(self, client, admin_session, db_session, admin_user):
        from database.models.document import Document, DocumentStatus as DocStatusEnum

        doc = Document(
            id=uuid.uuid4(),
            title="Patchable Doc",
            file_hash="patchhash999",
            status=DocStatusEnum.PENDING,
            uploaded_by_id=admin_user.id,
        )
        db_session.add(doc)
        await db_session.commit()

        resp = await client.patch(
            f"/v1/admin/documents/{doc.id}",
            json={"uploaded_by_id": None},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 200
        assert resp.json()["uploaded_by_id"] is None


# ---------------------------------------------------------------------------
# Ingest-text
# ---------------------------------------------------------------------------

class TestIngestText:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.post(
            f"/v1/admin/documents/{uuid.uuid4()}/ingest-text",
            content="hello",
            headers={"Content-Type": "text/plain"},
        )
        assert resp.status_code == 401

    async def test_nonexistent_document_returns_404(self, client, admin_session):
        resp = await client.post(
            f"/v1/admin/documents/{uuid.uuid4()}/ingest-text",
            content="some text",
            headers={
                **_auth(admin_session),
                "Content-Type": "text/plain",
            },
        )
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_400(self, client, admin_session):
        resp = await client.post(
            "/v1/admin/documents/bad-uuid/ingest-text",
            content="text",
            headers={
                **_auth(admin_session),
                "Content-Type": "text/plain",
            },
        )
        assert resp.status_code == 400

    async def test_valid_document_is_ingested(self, client, admin_session, db_session):
        from database.models.document import Document, DocumentStatus as DocStatusEnum

        doc = Document(
            id=uuid.uuid4(),
            title="Ingest Text Doc",
            file_hash="ingesttexthash1",
            status=DocStatusEnum.PENDING,
            uploaded_by_id=None,
        )
        db_session.add(doc)
        await db_session.commit()

        resp = await client.post(
            f"/v1/admin/documents/{doc.id}/ingest-text",
            content="VAT is charged at 15 percent on taxable goods and services.",
            headers={
                **_auth(admin_session),
                "Content-Type": "text/plain",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_id"] == str(doc.id)
        assert data["status"] == "indexed"

    async def test_empty_text_returns_400(self, client, admin_session, db_session):
        from database.models.document import Document, DocumentStatus as DocStatusEnum

        doc = Document(
            id=uuid.uuid4(),
            title="Empty Text Doc",
            file_hash="emptytexthash1",
            status=DocStatusEnum.PENDING,
            uploaded_by_id=None,
        )
        db_session.add(doc)
        await db_session.commit()

        resp = await client.post(
            f"/v1/admin/documents/{doc.id}/ingest-text",
            content="   ",
            headers={
                **_auth(admin_session),
                "Content-Type": "text/plain",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Scrape trigger
# ---------------------------------------------------------------------------

class TestAdminScrape:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.post("/v1/admin/scrape")
        assert resp.status_code == 401

    async def test_editor_cannot_trigger_scrape(self, client, editor_session):
        resp = await client.post("/v1/admin/scrape", headers=_auth(editor_session))
        assert resp.status_code == 403

    async def test_superadmin_triggers_scrape(self, client, admin_session):
        with patch(
            "apps.api.routers.admin.WebScraper",
            return_value=AsyncMock(scan_for_updates=AsyncMock(return_value={"inserted": 0, "skipped": 0, "errors": 0})),
        ):
            resp = await client.post("/v1/admin/scrape", headers=_auth(admin_session))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "stats" in data


# ---------------------------------------------------------------------------
# Patch user
# ---------------------------------------------------------------------------

class TestPatchAdminUser:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.patch(f"/v1/admin/users/{uuid.uuid4()}", json={})
        assert resp.status_code == 401

    async def test_editor_cannot_patch_user(self, client, editor_session):
        resp = await client.patch(
            f"/v1/admin/users/{uuid.uuid4()}",
            json={"role": "editor"},
            headers=_auth(editor_session),
        )
        assert resp.status_code == 403

    async def test_invalid_uuid_returns_400(self, client, admin_session):
        resp = await client.patch(
            "/v1/admin/users/not-a-uuid",
            json={"role": "editor"},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 400

    async def test_nonexistent_user_returns_404(self, client, admin_session):
        resp = await client.patch(
            f"/v1/admin/users/{uuid.uuid4()}",
            json={"role": "editor"},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 404

    async def test_invalid_role_returns_400(self, client, admin_session, editor_user):
        resp = await client.patch(
            f"/v1/admin/users/{editor_user.id}",
            json={"role": "god"},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 400

    async def test_superadmin_can_change_role(self, client, admin_session, editor_user):
        resp = await client.patch(
            f"/v1/admin/users/{editor_user.id}",
            json={"role": "superadmin"},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "superadmin"

    async def test_superadmin_can_deactivate_other_user(self, client, admin_session, editor_user):
        resp = await client.patch(
            f"/v1/admin/users/{editor_user.id}",
            json={"is_active": False},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_cannot_deactivate_self(self, client, admin_session, admin_user):
        resp = await client.patch(
            f"/v1/admin/users/{admin_user.id}",
            json={"is_active": False},
            headers=_auth(admin_session),
        )
        assert resp.status_code == 400
        assert "own account" in resp.json()["detail"].lower()
