"""Document thumbnail helpers (first-page preview for PDFs)."""

from __future__ import annotations

import os
from pathlib import Path

import fitz
from PIL import Image

from ai_engine.scraper.storage import document_storage_root


def thumbnail_storage_root() -> Path:
    raw = os.getenv("DOCUMENT_THUMBNAIL_DIR", "data/thumbnails")
    return Path(raw).expanduser().resolve()


def thumbnail_path_for_document(doc_id: str) -> Path:
    return thumbnail_storage_root() / f"{doc_id}.jpg"


def generate_pdf_thumbnail(
    *,
    doc_id: str,
    storage_path: str,
    width: int = 320,
) -> Path:
    """
    Generate a JPEG thumbnail from PDF first page and return the output path.

    The file is cached at ``DOCUMENT_THUMBNAIL_DIR/{doc_id}.jpg`` and overwritten
    when re-generated.
    """
    src = document_storage_root() / storage_path
    if not src.is_file():
        raise FileNotFoundError(f"Document file not found: {src}")

    out_path = thumbnail_path_for_document(doc_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(src)
    try:
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        mode = "RGB" if pix.n == 3 else "RGBA"
        image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        if mode == "RGBA":
            image = image.convert("RGB")
        if image.width > width:
            scale = width / float(image.width)
            image = image.resize(
                (width, int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )
        image.save(out_path, format="JPEG", quality=80, optimize=True)
    finally:
        doc.close()
    return out_path
