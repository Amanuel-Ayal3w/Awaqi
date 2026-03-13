"""
PDF text extraction using Gemini Flash.

Sends PDF pages to gemini-2.5-flash to extract text, handling both
digitally-born PDFs and scanned/OCR documents natively.
"""

import io
import logging
from dataclasses import dataclass

from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# Gemini Flash handles up to ~100 pages per request comfortably,
# but we batch in groups of 10 for reliability and rate-limit safety.
_PAGES_PER_BATCH = 10


@dataclass
class PageText:
    """Extracted text from a single PDF page."""
    page_number: int  # 1-indexed
    text: str


def _split_pdf_pages(pdf_bytes: bytes) -> list[bytes]:
    """Split a PDF into individual single-page PDFs (as bytes)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_pdfs: list[bytes] = []
    for page in reader.pages:
        writer = PdfWriter()
        writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        page_pdfs.append(buf.getvalue())
    return page_pdfs


async def extract_text(pdf_bytes: bytes, client: genai.Client | None = None) -> list[PageText]:
    """
    Extract text from every page of a PDF using Gemini Flash.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        client: Optional pre-configured genai.Client.

    Returns:
        List of PageText with 1-indexed page numbers.
    """
    if client is None:
        client = genai.Client()

    page_pdfs = _split_pdf_pages(pdf_bytes)
    total_pages = len(page_pdfs)
    logger.info("Extracting text from %d pages via Gemini Flash", total_pages)

    results: list[PageText] = []

    # Process pages in batches
    for batch_start in range(0, total_pages, _PAGES_PER_BATCH):
        batch_end = min(batch_start + _PAGES_PER_BATCH, total_pages)
        batch_pages = page_pdfs[batch_start:batch_end]

        for i, page_pdf in enumerate(batch_pages):
            page_num = batch_start + i + 1  # 1-indexed
            try:
                text = await _extract_single_page(client, page_pdf, page_num)
                results.append(PageText(page_number=page_num, text=text))
            except Exception:
                logger.exception("Failed to extract text from page %d", page_num)
                results.append(PageText(page_number=page_num, text=""))

    return results


async def _extract_single_page(
    client: genai.Client,
    page_pdf: bytes,
    page_num: int,
) -> str:
    """Send a single PDF page to Gemini Flash for text extraction."""
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part.from_bytes(
                        data=page_pdf,
                        mime_type="application/pdf",
                    ),
                    types.Part.from_text(
                        text=(
                            "Extract ALL text from this document page exactly as written. "
                            "Preserve the original language (Amharic or English). "
                            "Return ONLY the extracted text, no commentary or formatting."
                        )
                    ),
                ]
            )
        ],
    )
    text = response.text or ""
    logger.debug("Page %d: extracted %d chars", page_num, len(text))
    return text.strip()
