"""RQ job: single-document ingestion with Redis progress reporting.

Used when an admin uploads a document via the UI. The upload endpoint saves
the file bytes to the DB + disk, then enqueues this job so the heavy
embedding work runs in the background.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from apps.api.queue.progress import publish_progress

logger = logging.getLogger(__name__)


def run_ingest_job(
    job_id: str,
    doc_id: str,
    file_bytes: bytes,
    mime_type: str,
    filename: str,
) -> str:
    """RQ job function: ingest a document from raw bytes with progress updates.

    Returns the final document status string.
    """

    publish_progress(job_id, 5, "Starting ingestion", "running")

    async def _run() -> str:
        from ai_engine.ingest import ingest_bytes_for_document
        from database.db import AsyncSessionLocal
        from database.models.document import Document
        from sqlalchemy import select

        publish_progress(job_id, 10, "Loading document record", "running")

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == uuid.UUID(doc_id))
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                raise ValueError(f"Document {doc_id} not found")

            publish_progress(job_id, 20, "Extracting text", "running")
            await ingest_bytes_for_document(
                db,
                doc,
                file_bytes,
                mime_type=mime_type,
                filename=filename,
                genai_client=None,
            )
            await db.refresh(doc)
            final_status = str(getattr(doc.status, "value", doc.status))

        return final_status

    try:
        final_status = asyncio.run(_run())
        if final_status == "indexed":
            publish_progress(job_id, 100, "Indexed successfully", "done")
        elif final_status == "requires_manual_review":
            publish_progress(job_id, 100, "Needs manual review", "done")
        else:
            publish_progress(job_id, 100, f"Finished: {final_status}", "done")
        return final_status
    except Exception as exc:
        logger.exception("ingest_job_failed job_id=%s doc_id=%s", job_id, doc_id)
        publish_progress(job_id, 0, f"Failed: {exc!s:.120}", "failed")
        raise
