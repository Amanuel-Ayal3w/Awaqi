# Awaqi implementation phases

This document turns the **Software Requirements Specification** (`SRS Suport Bot AI.md`), **Software Design Specification** (`SDS Support Bot AI.md`), and your **Linear export** (`Awaqi › All issues.csv`) into an ordered delivery plan. **Ingestion is sequenced first** because retrieval, citations, and evaluation all depend on a correct knowledge base.

> **Authoritative specs:** SRS defines *what* (FR-01–FR-09 in §3.2.1, UC-02/UC-03, NFRs). SDS defines *how* (Ingestion subsystem: WebScraper, DocumentProcessor/OCR, ChunkingService; PostgreSQL + pgvector; PostgreSQL FTS for sparse retrieval; multilingual-e5-large + cosine in design narrative). The CSV issues refine several FRs (token windows, HTML/PDF/OCR routing, atomic re-index, BM25 in Postgres, etc.). Where SRS and CSV differ, **treat the CSV acceptance criteria as the implementation contract** unless the team explicitly relaxes them.

> **Current codebase snapshot (for gap planning):** `packages/ai-engine` already has an admin-driven PDF path (`ingest_pdf`: Gemini-based extraction → character-window chunking → Gemini `gemini-embedding-001` embeddings → `document_chunks`). That is a **prototype** relative to SRS/SDS/CSV: model choice, chunking strategy, scraper, OCR branch, BM25 column/index, and several metadata fields are still to be aligned.

---

## Traceability: ingestion vs documents

| Theme | SRS | SDS | CSV issues |
| --- | --- | --- | --- |
| Scheduled scrape | FR-01, UC-02 | §2.1 Ingestion, WebScraper | AWA-5 |
| Dedup / registry | UC-02 step 3, 8 (“hash registry”) | WebScraper `scanForUpdates` | AWA-7 |
| Extraction (PDF/HTML/OCR) | FR-02 (PDF/Word + Amharic) | DocumentProcessor (OCR) | AWA-6 |
| Amharic / Ethiopic integrity | FR-02, NFR-16 area | Tokenization notes | AWA-10, AWA-74 |
| Low OCR confidence → human | UC-02 A3 | — | AWA-9 |
| Manual / ad-hoc scrape | UC-03 admin path | Admin `forceScrape` | AWA-11 |
| Chunking + overlap | FR-03 | §4.6.5 sliding window + overlap | AWA-12 |
| Chunk metadata | Citation use cases | Document.chunk metadata | AWA-13 |
| Embeddings 1024 + cosine | §3.9 stack | §4.6.2, E5 embedder in class diagram | AWA-14 |
| BM25 / hybrid sparse leg | Hybrid architecture | PostgreSQLFullTextAdapter, §4.8.2 | AWA-15 |
| Atomic re-index | UC-02 “no duplicate vectors” | Data integrity NFR | AWA-12, AWA-16 |
| Admin progress UI | UC-03 step 6 | Document `processStatus` | AWA-17 |
| Duplicate upload UX | UC-03 A3 | Admin upload | AWA-39 |

---

## How to read each phase

For every phase below:

1. **Completes (issues):** Linear IDs that should move to *Done* when the phase exit criteria are met.
2. **Engineering tasks:** Concrete work units.
3. **Exit criteria:** What “perfect” means for that slice.
4. **How to test:** Commands, checks, and automated tests to run (many CSV lines already spell out verification style).

---

# Part A — Ingestion track (do this first)

## Phase A1 — Requirements baseline & ingestion architecture

**Goal:** Freeze interfaces between scraper, extractor, chunker, embedder, and DB so later phases do not thrash.

**Completes (issues):** *None closed yet*; this phase unblocks AWA-5 through AWA-17.

**Tasks**

- Write a short **ingestion architecture note** (in-repo code comments + `ARCHITECTURE.md` section is enough): state machine for `documents.status`, idempotency keys (`file_hash`, optional `source_url` + `content_length` per AWA-7), and transaction boundaries for “delete old chunks then insert new” (AWA-16).
- Align naming with SDS classes: `WebScraper`, `DocumentProcessor`, `ChunkingService`, ports `IVectorStore` / `ISparseSearch` (implementation can stay in `packages/ai-engine`).

**Exit criteria**

- Document lifecycle and dedup keys are documented and agreed.
- No ingestion code change required to understand transaction boundaries for re-index.

**How to test**

- Review only: walk through UC-02 and UC-03 in SRS with the team and tick alignment with the note.

---

## Phase A2 — Document registry, deduplication, and atomic re-index

**Goal:** Never double-ingest the same bytes; re-indexing one document must not leave orphan embeddings (SRS UC-02, CSV AWA-7, AWA-16, AWA-39).

**Completes (issues):** **AWA-7**, **AWA-16**, **AWA-39** (backend/data layer; UI confirmation dialog can be minimal in API first).

**Tasks**

- **Registry:** Persist SHA-256 of raw file bytes (already partially present on `documents.file_hash`). Extend as needed for **URL + declared size** if you adopt AWA-7 literally alongside byte hash.
- **Transactions:** On re-index or overwrite, in one DB transaction: `DELETE` all `document_chunks` for `document_id` → insert new rows → update document status (AWA-16).
- **Duplicate upload API:** If content hash matches an existing indexed doc, return a structured response `{ duplicate_of, choices: ["cancel", "overwrite"] }`; overwrite uses the same transactional delete path (AWA-39).

**Exit criteria**

- Running ingest twice on identical bytes does not increase chunk count.
- Re-index replaces chunk count exactly (no doubling).

**How to test**

- **Integration (automated):** Seed DB with one document and chunks; call re-ingest; assert `COUNT(document_chunks)` equals new pipeline output only.
- **Manual:** Upload same PDF twice; second request returns duplicate payload until overwrite chosen.

---

## Phase A3 — Scheduled and ad-hoc acquisition (MoR)

**Goal:** Automated daily job and admin-triggered run as in FR-01 / UC-02 / SDS WebScraper (CSV **AWA-5**, **AWA-11**).

**Completes (issues):** **AWA-5**, **AWA-11**.

**Tasks**

- Implement `WebScraper.scanForUpdates` / `downloadFile`: crawl **Proclamations, Directives, Announcements** sections of mor.gov.et (SRS UC-02; confirm live URLs and HTML structure in code comments when implemented).
- **Scheduler:** Cron or worker (APScheduler, Celery beat, or k8s CronJob) at **00:00 EAT** with timezone `Africa/Addis_Ababa`.
- **Ad-hoc:** Admin API `POST /admin/scrape` or equivalent calling the same pipeline entrypoint as the job (SDS Admin `forceScrape`).
- **Resilience:** Retries with backoff on HTTP errors (SRS UC-02 A2); structured logs **without PII** (prepare for AWA-64).

**Exit criteria**

- Job enqueue + completion logged; second run on unchanged site performs no downloads (registry from A2).

**How to test**

- **Unit:** Mock HTTP; assert discovered links filtered by registry.
- **Integration / staging:** Point at a fixture mirror or recorded HTML; run job twice; assert idempotency.
- **CSV-style check (AWA-5):** In staging, assert log timestamp within **00:00 EAT ±5 min** when the scheduler is enabled (or document equivalent CI simulation using frozen clock).

---

## Phase A4 — Multi-modal extraction (HTML, PDF text layer, OCR fallback)

**Goal:** Meet **AWA-6** and SRS FR-02 scope: HTML text, PyMuPDF for text PDFs, Tesseract (or equivalent) when no text layer — with automatic mode selection.

**Completes (issues):** **AWA-6** (partial overlap with current Gemini PDF extraction — **replace or gate** behind a “legacy” flag until parity tests pass).

**Tasks**

- **HTML:** Readability-style main content extraction + encoding detection (UTF-8).
- **PDF:** PyMuPDF text extraction; detect empty page text → OCR branch.
- **OCR:** Tesseract with language packs including **amh** where available; capture mean confidence per page.
- **Unified output:** Same internal representation as today (`PageText` or successor) so chunking stays agnostic.

**Exit criteria**

- Fixture suite: one HTML page, one native PDF, one scanned PDF passes extraction tests.

**How to test**

- **Unit (per mode):** Golden files under `packages/ai-engine/tests/fixtures/`; assert non-empty text and stable hashes for known strings.
- **Manual:** Run pipeline on a known MoR PDF and compare extracted article headings to source.

---

## Phase A5 — OCR quality gate and manual review path

**Goal:** SRS UC-02 A3 + **AWA-9**: do not index garbage scans; surface admin workflow.

**Completes (issues):** **AWA-9**.

**Tasks**

- If OCR mean confidence **< 0.7**, set document status to **`requires_manual_review`**, skip chunk/embed/index writes, and expose status in admin list API.
- Admin endpoint to attach **corrected plain text** and restart ingestion from text (bypass OCR).

**Exit criteria**

- Low-confidence fixture never produces searchable chunks.

**How to test**

- **Integration:** Deliberately degraded scan fixture → status flag set, chunk count 0.
- **UI / API:** Admin can upload replacement `.txt` and move document to indexed.

---

## Phase A6 — Ethiopic Unicode integrity (ingestion path)

**Goal:** **AWA-10**, **AWA-74**, SRS FR-02 / NFR on Amharic: characters survive extract → chunk → DB round-trip.

**Completes (issues):** **AWA-10**, **AWA-74** (ingestion scope; chat display may still need a separate pass).

**Tasks**

- Normalize Unicode (NFC), forbid lossy transcoding; ensure DB driver and JSONB paths use UTF-8 end-to-end.
- Add fixture with known Ethiopic codepoints (U+1200–U+137F range called out in AWA-10).

**Exit criteria**

- Byte-for-byte or NFC-normalized equality of known Amharic strings after round-trip.

**How to test**

- **Automated:** Round-trip test: fixture → extract → store → read → compare codepoints.
- **SQL:** `SELECT content FROM document_chunks WHERE ...` and verify in psql with UTF-8 client encoding.

---

## Phase A7 — Spec-compliant chunking

**Goal:** **AWA-12**: **512–1024 tokens**, sentence-boundary-aware sliding window, **~10% token overlap**, consecutive overlap **≥ 50 tokens** (per CSV verification).

**Completes (issues):** **AWA-12**.

**Tasks**

- Replace or augment char-only windows with **tokenizer-based** windows (sentencepiece / transformers tokenizer matching the embedding model’s family is ideal for e5).
- Enforce max token cap and overlap statistics in tests.

**Exit criteria**

- Automated tests enforce max ≤1024 tokens and pairwise overlap ≥50 tokens on synthetic long text.

**How to test**

- **Unit:** Token counts via the same tokenizer used at chunk time.
- **Property / fuzz:** Random legal-like text generator still respects bounds.

---

## Phase A8 — Chunk metadata schema (citations-ready)

**Goal:** **AWA-13**: every chunk carries `document_id`, `chunk_id`, `source_url`, `document_title`, `proclamation_number`, `article_number`, `effective_date`, `language`, `created_at` (store as columns **or** structured JSONB with DB constraints / generated columns as appropriate).

**Completes (issues):** **AWA-13**.

**Tasks**

- Extend DB schema + migrations; populate from scraper HTML/PDF metadata and heading heuristics (article numbers).
- Ensure metadata is returned on retrieval APIs for later citation pills (**AWA-27**, **AWA-90**).

**Exit criteria**

- Schema validation test: representative indexed chunks have all required fields non-null.

**How to test**

- **Alembic migration** applied on clean DB; seed script; `pytest` asserting non-null metadata keys.

---

## Phase A9 — Embeddings: multilingual-e5-large + pgvector cosine

**Goal:** **AWA-14**, SDS §4.6.2 / stack table: **1024-dim e5 embeddings**, cosine distance in pgvector (replace or dual-run Gemini embeddings during migration if needed).

**Completes (issues):** **AWA-14**.

**Tasks**

- Implement `E5Embedder` adapter (`passage: ` / `query: ` prefixes per model card) for documents vs queries.
- Batch GPU/CPU inference with performance target in mind (CSV AWA-19 mentions query latency separately).
- Re-index existing corpus after switch (coordinate with A2 atomic re-index).

**Exit criteria**

- Integration test: sample chunks have `vector_dims(embedding) = 1024` and distance operator matches cosine expectation on toy vectors.

**How to test**

- **Unit:** Known input vector cosine against reference implementation or small golden file.
- **Integration:** `SELECT embedding <=> '[...]'::vector` sanity check.

---

## Phase A10 — BM25-style full-text index (PostgreSQL)

**Goal:** **AWA-15**, SDS hybrid retrieval: maintain **PostgreSQL FTS** (GIN `tsvector`) over chunk text for hybrid retrieval later.

**Completes (issues):** **AWA-15**.

**Tasks**

- Add `tsvector` column + trigger or application-side update on insert/update.
- Implement `to_tsvector` config: likely **simple** + custom Amharic handling (may need unaccent / dictionary choices — document decision).
- Keyword integration test query returns non-empty hits for a known rare token from fixtures.

**Exit criteria**

- BM25/FTS path returns known fixture chunk for controlled keyword.

**How to test**

- **Integration:** SQL or repository method `search_bm25('VAT-285')`-style query against seeded data.
- **Regression:** Ensure index is used (`EXPLAIN` in CI optional).

---

## Phase A11 — Admin UX: progress stages and wiring

**Goal:** **AWA-17** (+ supports UC-03): Parsing → Chunking → Embedding → Indexing; status **Active/Searchable** only when all complete.

**Completes (issues):** **AWA-17** (UI + backend events).

**Tasks**

- Emit stage transitions via DB status sub-states or a `document_processing_events` table + SSE/WebSocket or polling endpoint.
- Next.js admin screen binds to those stages (reuse existing admin area patterns).

**Exit criteria**

- Upload shows all four stages in order; failed stage surfaces error without marking searchable.

**How to test**

- **UI test (Playwright or manual script):** Upload sample file; observe stage sequence.
- **API contract test:** Stage endpoint returns monotonic progression.

---

### Ingestion track summary — issue completion by phase

| Phase | Issues completed when done |
| --- | --- |
| A1 | (none — foundation) |
| A2 | AWA-7, AWA-16, AWA-39 |
| A3 | AWA-5, AWA-11 |
| A4 | AWA-6 |
| A5 | AWA-9 |
| A6 | AWA-10, AWA-74 |
| A7 | AWA-12 |
| A8 | AWA-13 |
| A9 | AWA-14 |
| A10 | AWA-15 |
| A11 | AWA-17 |

---

# Part B — Post-ingestion (retrieval, chat, admin analytics, ops)

These phases depend on Part A being stable enough to index real chunks.

## Phase B1 — Query-side NLU and embeddings

**Completes:** **AWA-18** (fastText language ID + mixed logging), **AWA-19** (category-specific **query** prefix for e5 `query: ` embeddings).

**How to test:** Unit fixtures for Amharic/English/mixed; timing test for embedding latency on target hardware (per AWA-19).

---

## Phase B2 — Hybrid retrieval + RAG answer path

**Completes:** Retrieval fusion (RRF per SDS), confidence thresholds, stub replacement in chat. Prerequisite issues from CSV not in your export snippet may exist for RRF/reranker — track separately.

**How to test:** Retrieval-only integration tests with known queries hitting BM25 + vector.

---

## Phase B3 — Citations in API and UI

**Completes:** **AWA-27**, **AWA-90** (pills + detail view).

**How to test:** Parser on assistant messages or structured citation JSON; assert ≥1 citation with title, proclamation #, article #.

---

## Phase B4 — Safety and abuse handling

**Completes:** **AWA-28**.

**How to test:** Fixture queries → polite refusal message.

---

## Phase B5 — Saved chats, export, bookmarks

**Completes:** **AWA-35**.

**How to test:** UI flows per CSV (PDF/text export, bookmark citation, delete session).

---

## Phase B6 — Admin analytics and evaluation jobs

**Completes:** **AWA-40** (health metrics endpoint + dashboard), **AWA-43** (monthly EM / F1 / BERTScore pipeline).

**How to test:** Integration on metrics endpoint fields; offline evaluation script on seeded 100-query set.

---

## Phase B7 — Platform, security, and reliability

**Completes:** **AWA-92** staging, **AWA-96** TLS/domain, **AWA-97** error tracking, **AWA-98** alerts, **AWA-64** (no PII in logs/DB — audit ingestion + chat logging).

**How to test:** Staging deploy checklist; Sentry DSN smoke; synthetic alert; static audit for forbidden fields in log calls.

---

# Suggested sequencing (dependencies)

```text
A1 baseline
  → A2 registry/atomicity (blocks everything)
    → A3 acquisition
    → A4 extraction
      → A5 OCR gate
      → A6 Unicode
        → A7 chunking
          → A8 metadata
            → A9 embeddings
              → A10 BM25
                → A11 admin progress
B1 NLU/query embeddings
B2 hybrid retrieval
B3 citations UI/API
B4 safety
B5 saved chats
B6 analytics/eval
B7 platform hardening
```

---

# Global testing commands (repo)

From `AGENTS.md` and package layout:

- **DB migrations:** `cd packages/database && uv run alembic upgrade head`
- **API health:** `curl -s http://localhost:8000/health`
- **Python lint:** `uv run ruff check .` (from repo root)
- **Frontend types:** `cd apps/web && npx tsc --noEmit`

Add **`pytest`** suites under `packages/ai-engine/tests/` and `apps/api/tests/` as ingestion matures (the repo notes tests are not yet pervasive).

---

## Notes on spec vs code (keep current as ingestion evolves)

| Topic | SRS / SDS / CSV | Current code (verify in tree) |
| --- | --- | --- |
| Embeddings | multilingual-e5-large, cosine | **Primary path:** `ingest.py` + `e5_embedder.py` (pgvector). **`embedder.py`** still holds Gemini embeddings for any legacy callers — grep before assuming one path. |
| Chunking | 512–1024 tokens, overlap rules | **`ChunkingService` / `chunker_tokens.py`** implement tokenizer windows; older **`chunker.py`** char windows may still exist for non-ingest tools. |
| Extraction | HTML + PyMuPDF + Tesseract | **`document_processor.py`** `INGEST_EXTRACTOR=native` (default). **`extractor.py`** remains optional Gemini path. |
| Sparse retrieval | PostgreSQL FTS (AWA-15) | **`content_tsv`** generated column + GIN + `fts.py` (`plainto_tsquery` / `ts_rank_cd`). Not a separate “BM25” named index, but meets hybrid sparse leg. |

---

## Linear issue evaluation matrix (authoritative)

Source: **`Awaqi › All issues.csv`** (export in repo). **Every exported ticket is evaluated below** against the codebase *as of the last edit to this file*. Status labels:

- **Meets** — Core acceptance is implemented; remaining work is mostly tests, polish, or ops outside the repo.
- **Partial** — Substantial code exists but gaps remain vs the CSV wording (model, UX, verification, or scope).
- **Not met** — Missing or only placeholder.

| ID | Evaluation | What exists in code | Gaps vs CSV / SRS (what “Done” still needs) |
| --- | --- | --- | --- |
| **AWA-5** | Partial | `apps/api/main.py` — APScheduler daily job **00:00** `Africa/Addis_Ababa` when `SCRAPER_SCHEDULER_ENABLED`; MoR pipeline via scraper. | Automated verification of cron log at 00:00 ±5 min; prove scheduler enabled in deployed env. |
| **AWA-6** | Partial | `document_processor.py` — HTML, PyMuPDF, Tesseract (`INGEST_EXTRACTOR=native` default); Gemini path optional. | Full fixture suite per mode; confirm admin/uploads never silently use Gemini unless configured. |
| **AWA-7** | Partial | `mor_scraper.py` — registry / dedup by logical key (`registry_key`, URL + size pattern per comments). | Strict “Document Registry table” wording + integration test: second scrape run downloads **zero** new files. |
| **AWA-9** | Partial | `OCR_CONFIDENCE_FAIL_THRESHOLD` 0.7; `requires_manual_review` status; `ingest_plain_text` + admin ingest-text for correction. | End-to-end test + admin UI clarity for low-confidence fixture; confirm **zero** chunks when flagged. |
| **AWA-10** | Partial | `text_utils.py` NFC normalization; tests under `packages/ai-engine/tests/`. | Full pipeline + **chat UI** round-trip proof (pairs with **AWA-74**). |
| **AWA-11** | Meets | `POST /v1/admin/scrape` in `apps/api/routers/admin.py`. | Optional: Playwright “Sync” click → log correlation (CSV UI verification). |
| **AWA-12** | Partial | `chunking_service.py` / `chunker_tokens.py` — token windows aligned to e5 tokenizer. | Automated bounds: max ≤1024 tokens, consecutive overlap ≥50 tokens, ~10% overlap (CSV numbers). |
| **AWA-13** | Partial | `chunk_metadata` JSONB populated in `ingest.py` with document/chunk ids, title, proc/article heuristics, dates, language. | Schema/validation: CSV asks **non-null** metadata for representative chunks — many fields can still be empty strings. |
| **AWA-14** | Meets | `e5_embedder.py` + `intfloat/multilingual-e5-large`; vectors in pgvector; ingest uses `embed_passages_sync`. | CI integration test: `vector_dims(embedding) = 1024` on seeded row. |
| **AWA-15** | Meets | Migration `0005_phase_a_ingestion.py` — `content_tsv` STORED + GIN; `packages/database/src/database/fts.py`. | Optional: `EXPLAIN` / ranking parity tests; document language config for Amharic if needed. |
| **AWA-16** | Meets | `ingest.py` — `DELETE` chunks for `document_id` then bulk insert + `indexed` in one commit block in `_ingest_from_pages`. | Integration test proving no doubling under concurrency (CSV verification). |
| **AWA-17** | Partial | `processing_stage` on documents; admin list/detail shows stage (`knowledge-base`, `documents` pages). | **Real-time** four-stage indicator + UI test “Parsing → Chunking → Embedding → Indexing” (CSV). |
| **AWA-18** | Partial | `query_nlu.py` — Ethiopic/Latin heuristic + `mixed`; logged from chat router. | Replace with **FastText** ID + dominant-language rule per CSV; unit fixtures as specified. |
| **AWA-19** | Partial | `build_e5_query_text` + `taxpayer_category` on API; `query:` prefix in e5 embedder. | Bind category from **authenticated user profile** (not only request field); embedding latency under **200 ms** on target HW (CSV). |
| **AWA-27** | Partial | Structured `Citation` in API; chat UI pills + expand excerpt in `MessageList.tsx`. | **Every factual** response must cite (enforce in RAG); automated parser test; pills must show proc **and** article when present. |
| **AWA-28** | Partial | `safety.py` — small rules + polite refusal; no raw query in refusal logs. | Lightweight **classifier** breadth (off-topic, abuse); expanded fixture suite per CSV. |
| **AWA-35** | Partial | `GET /v1/chat/export/{session_id}` plain text; “Export transcript” in chat UI. | PDF export; **bookmarks**; session list with timestamps; delete session / delete all history (registered user flows). |
| **AWA-39** | Partial | Admin upload: duplicate `file_hash` returns structured `duplicate_of` + `choices`; overwrite path. | Full admin **dialog** UX test (CSV); ensure overwrite uses same atomic delete path (align with AWA-16 tests). |
| **AWA-40** | Partial | `GET /v1/admin/system-health` — DB + Redis; dashboard cards on admin home. | CPU/RAM, rolling LLM latency, **vector** query latency, **Telegram** webhook, **30 s** refresh — all in CSV. |
| **AWA-43** | Not met | — | Monthly EM / F1 / BERTScore job, 100-query gold set, dashboard surfacing, integration test. |
| **AWA-64** | Not met | Partial awareness in comments (`safety.py`). | Repo-wide audit: logs, DB, tracing — no TIN/name/phone/email; formal checklist + tooling. |
| **AWA-74** | Partial | Same as AWA-10 track; NFR is stricter (“zero corruption”). | Dedicated end-to-end Ethiopic range proof + monitoring. |
| **AWA-90** | Partial | Expandable citation panel shows excerpt + proc/article/page. | **Navigate to source** (document viewer / deep link to MoR URL / PDF page) — CSV “detail view”. |
| **AWA-92** | Not met | — | Staging environment + access policy + E2E checklist. |
| **AWA-96** | Not met | — | TLS, domain, HTTPS routing (ops / infra). |
| **AWA-97** | Not met | — | Sentry (or equivalent) FE + BE. |
| **AWA-98** | Not met | — | Alerts for scraper, indexing, chat, deploy failures. |

### Summary counts (this export)

| Bucket | Count | IDs |
| --- | ---: | --- |
| **Meets** | 4 | AWA-11, AWA-14, AWA-15, AWA-16 |
| **Partial** | 17 | AWA-5, 6, 7, 9, 10, 12, 13, 17, 18, 19, 27, 28, 35, 39, 40, 74, 90 |
| **Not met** | 6 | AWA-43, AWA-64, AWA-92, AWA-96, AWA-97, AWA-98 |

**Process:** When Linear status changes, update the **Evaluation** and **Gaps** columns here so release reviews always have **one table that covers every exported ticket**.
