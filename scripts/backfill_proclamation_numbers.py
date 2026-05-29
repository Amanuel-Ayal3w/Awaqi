"""Backfill ``document.proclamation_number`` for rows that were ingested before
the heuristics regex was widened to accept dashes as separators.

Usage:
    uv run --package api python scripts/backfill_proclamation_numbers.py
    uv run --package api python scripts/backfill_proclamation_numbers.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "ai-engine" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "database" / "src"))

from ai_engine.heuristics import guess_proclamation_number
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentChunk
from sqlalchemy import select


async def run(dry_run: bool) -> int:
    patched_docs = 0
    patched_chunks = 0

    async with AsyncSessionLocal() as session:
        docs = (await session.execute(select(Document))).scalars().all()
        for doc in docs:
            guess = guess_proclamation_number(doc.title or "")
            if not guess:
                continue
            if doc.proclamation_number == guess:
                continue

            print(
                f"  doc {doc.id}  title={doc.title!r}  "
                f"{doc.proclamation_number!r} -> {guess!r}"
            )
            if not dry_run:
                doc.proclamation_number = guess
                patched_docs += 1

                # Also stamp chunk_metadata so chunks ingested with empty meta
                # become matchable without needing a full re-embed.
                chunks = (
                    await session.execute(
                        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
                    )
                ).scalars().all()
                for ch in chunks:
                    meta = dict(ch.chunk_metadata or {})
                    if meta.get("proclamation_number") == guess:
                        continue
                    meta["proclamation_number"] = guess
                    ch.chunk_metadata = meta
                    patched_chunks += 1

        if not dry_run:
            await session.commit()

    print()
    print(f"Patched {patched_docs} documents, {patched_chunks} chunks.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.dry_run))
