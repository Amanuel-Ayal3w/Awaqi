"""
Multi-modal document extraction (AWA-6).

``INGEST_EXTRACTOR``:
  - ``native`` (default): HTML / plain text / PDF via PyMuPDF + Tesseract fallback.
  - ``gemini``: legacy per-page PDF extraction via Gemini Flash (see ``extractor.py``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree as ET

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from google import genai

from ai_engine.extractor import PageText
from ai_engine.extractor import extract_text as extract_text_gemini
from ai_engine.text_utils import normalize_unicode_nfc

logger = logging.getLogger(__name__)

INGEST_EXTRACTOR = os.getenv("INGEST_EXTRACTOR", "native").lower()
MIN_TEXT_CHARS_FOR_NATIVE_PAGE = int(os.getenv("MIN_TEXT_CHARS_PER_PAGE", "40"))
OCR_LANGS = os.getenv("OCR_LANGS", "eng+amh")
OCR_CONFIDENCE_FAIL_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_FAIL_THRESHOLD", "0.7"))


@dataclass
class ExtractionOutcome:
    pages: list[PageText]
    requires_manual_review: bool
    review_reason: str | None = None


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _ocr_page(pdf_page: fitz.Page) -> tuple[str, float]:
    """Render page and OCR with Tesseract; return (text, mean_confidence 0..1)."""
    import pytesseract
    from PIL import Image

    mat = fitz.Matrix(2.0, 2.0)
    pix = pdf_page.get_pixmap(matrix=mat, alpha=False)
    mode = "RGB" if pix.n == 3 else "RGBA"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    if mode == "RGBA":
        img = img.convert("RGB")

    data = pytesseract.image_to_data(
        img, lang=OCR_LANGS, output_type=pytesseract.Output.DICT
    )
    confs: list[float] = []
    words: list[str] = []
    for i, conf in enumerate(data.get("conf", [])):
        try:
            c = float(conf)
        except (TypeError, ValueError):
            continue
        if c < 0:
            continue
        confs.append(c / 100.0)
        w = (data.get("text") or [""])[i]
        if w and w.strip():
            words.append(w)

    text = " ".join(words).strip()
    mean_conf = float(sum(confs) / len(confs)) if confs else 0.0
    return text, mean_conf


def _extract_pdf_native(pdf_bytes: bytes) -> ExtractionOutcome:
    """PyMuPDF text layer with OCR fallback per page."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PageText] = []
    ocr_confidences: list[float] = []

    try:
        for i in range(len(doc)):
            page = doc[i]
            raw = normalize_unicode_nfc((page.get_text("text") or "").strip())
            if len(raw) >= MIN_TEXT_CHARS_FOR_NATIVE_PAGE:
                pages.append(
                    PageText(
                        page_number=i + 1,
                        text=raw,
                        extraction_mode="pdf_text",
                        ocr_mean_confidence=None,
                    )
                )
                continue

            ocr_text, ocr_mean = _ocr_page(page)
            ocr_text = normalize_unicode_nfc(ocr_text)
            ocr_confidences.append(ocr_mean)
            pages.append(
                PageText(
                    page_number=i + 1,
                    text=ocr_text,
                    extraction_mode="ocr",
                    ocr_mean_confidence=ocr_mean,
                )
            )
    finally:
        doc.close()

    if not any(p.text.strip() for p in pages):
        return ExtractionOutcome(
            pages=[],
            requires_manual_review=False,
            review_reason="empty_extract",
        )

    mean_ocr = _mean(ocr_confidences)
    if mean_ocr is not None and mean_ocr < OCR_CONFIDENCE_FAIL_THRESHOLD:
        return ExtractionOutcome(
            pages=pages,
            requires_manual_review=True,
            review_reason="low_ocr_confidence",
        )

    return ExtractionOutcome(pages=pages, requires_manual_review=False)


def _extract_html(html_bytes: bytes) -> ExtractionOutcome:
    soup = BeautifulSoup(html_bytes, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = normalize_unicode_nfc(re.sub(r"\n{3,}", "\n\n", text))
    pages = [
        PageText(
            page_number=1,
            text=text,
            extraction_mode="html",
            ocr_mean_confidence=None,
        )
    ]
    return ExtractionOutcome(pages=pages, requires_manual_review=False)


def _extract_plain_text(data: bytes) -> ExtractionOutcome:
    text = normalize_unicode_nfc(data.decode("utf-8", errors="replace"))
    pages = [
        PageText(
            page_number=1,
            text=text,
            extraction_mode="manual_txt",
            ocr_mean_confidence=None,
        )
    ]
    return ExtractionOutcome(pages=pages, requires_manual_review=False)


def _extract_docx(data: bytes) -> ExtractionOutcome:
    """Pull paragraph text from OOXML (no external deps)."""
    try:
        text_parts: list[str] = []
        with zipfile.ZipFile(BytesIO(data)) as zf:
            with zf.open("word/document.xml") as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                for node in root.findall(".//w:p", ns):
                    runs = []
                    for t in node.findall(".//w:t", ns):
                        if t.text:
                            runs.append(t.text)
                    if runs:
                        text_parts.append("".join(runs))
        text = normalize_unicode_nfc("\n".join(text_parts))
    except (KeyError, OSError, ET.ParseError, zipfile.BadZipFile):
        return ExtractionOutcome(
            pages=[],
            requires_manual_review=False,
            review_reason="empty_extract",
        )
    pages = [
        PageText(
            page_number=1,
            text=text,
            extraction_mode="docx",
            ocr_mean_confidence=None,
        )
    ]
    return ExtractionOutcome(pages=pages, requires_manual_review=False)


async def extract_bytes(
    data: bytes,
    *,
    mime_type: str | None,
    filename: str | None,
    genai_client: genai.Client | None = None,
) -> ExtractionOutcome:
    """
    Route extraction based on MIME / filename.

    PDF:
      - ``INGEST_EXTRACTOR=gemini`` → Gemini per-page extraction.
      - otherwise → native PyMuPDF + OCR fallback.
    """
    name = (filename or "").lower()
    mt = (mime_type or "").split(";")[0].strip().lower()

    if mt in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ) or name.endswith(".docx"):
        return await asyncio.to_thread(_extract_docx, data)

    if mt == "application/pdf" or name.endswith(".pdf"):
        if INGEST_EXTRACTOR == "gemini":
            client = genai_client or genai.Client()
            pages = await extract_text_gemini(data, client=client)
            for p in pages:
                if not p.extraction_mode:
                    p.extraction_mode = "gemini"
            return ExtractionOutcome(pages=pages, requires_manual_review=False)
        return await asyncio.to_thread(_extract_pdf_native, data)

    if mt in ("text/html", "application/xhtml+xml") or name.endswith((".html", ".htm")):
        return await asyncio.to_thread(_extract_html, data)

    if mt.startswith("text/") or name.endswith(".txt"):
        return await asyncio.to_thread(_extract_plain_text, data)

    # Default: try UTF-8 text
    return await asyncio.to_thread(_extract_plain_text, data)


class DocumentProcessor:
    """SDS-aligned façade for multi-modal extraction (same behavior as ``extract_bytes``)."""

    @staticmethod
    async def extract_bytes(
        data: bytes,
        *,
        mime_type: str | None,
        filename: str | None,
        genai_client: genai.Client | None = None,
    ) -> ExtractionOutcome:
        return await extract_bytes(data, mime_type=mime_type, filename=filename, genai_client=genai_client)
