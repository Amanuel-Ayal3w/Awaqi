"""On-disk storage for downloaded regulatory PDFs."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID


def document_storage_root() -> Path:
    raw = os.getenv("DOCUMENT_STORAGE_DIR", "data/documents")
    return Path(raw).expanduser().resolve()


def save_document_pdf(document_id: UUID, pdf_bytes: bytes) -> str:
    """Write PDF bytes; returns relative storage path."""
    return save_document_file(document_id, pdf_bytes, "pdf")


def save_document_file(document_id: UUID, data: bytes, extension: str) -> str:
    """
    Write file bytes under ``DOCUMENT_STORAGE_DIR/{document_id}.{ext}``.

    Returns a relative storage path (filename only) for ``documents.storage_path``.
    """
    ext = extension.lstrip(".").lower()
    root = document_storage_root()
    root.mkdir(parents=True, exist_ok=True)
    rel = f"{document_id}.{ext}"
    path = root / rel
    path.write_bytes(data)
    return rel


def read_document_pdf(storage_path: str | None) -> bytes | None:
    return read_document_file(storage_path)


def read_document_file(storage_path: str | None) -> bytes | None:
    if not storage_path:
        return None
    path = document_storage_root() / storage_path
    if not path.is_file():
        return None
    return path.read_bytes()


def guess_media_type(storage_path: str | None) -> str:
    if not storage_path:
        return "application/octet-stream"
    ext = storage_path.rsplit(".", 1)[-1].lower() if "." in storage_path else ""
    return {
        "pdf": "application/pdf",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")
