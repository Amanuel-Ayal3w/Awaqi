# RAG Evaluation

A reproducible benchmark for the Awaqi retrieval + answer pipeline. Implements
the standard RAG evaluation stack and an LLM-as-judge scorer (1–10 per
question) that surface on the admin panel.

## What it measures

**Retrieval (top-k)** — computed by checking whether each retrieved chunk's
document `proclamation_number` matches the benchmark item's ground truth:

| Metric | What it tells you |
| --- | --- |
| `Hit@k` | Did the right document appear in the top-k at all? |
| `Precision@k` | Of the top-k, how many were relevant? |
| `Recall@k` | Of the relevant docs found, how many did we surface? |
| `MRR` | How highly ranked is the first relevant doc? |
| `NDCG@k` | Position-discounted relevance (the one to track over time) |

**Generation** — Gemini judges each candidate answer 1–10 on:

| Axis | What it tells you |
| --- | --- |
| `faithfulness` | Are claims grounded in the retrieved context? (catches hallucinations) |
| `answer_relevance` | Does the answer address the question? |
| `context_recall` | Did retrieval supply the facts the expected answer needs? |
| `correctness` | Does the answer match the expected ground-truth answer? |
| `overall` | Weighted aggregate: 0.30·correctness + 0.30·faithfulness + 0.20·relevance + 0.20·context_recall |

Plus `semantic_similarity` — cosine of `embed(expected)` vs `embed(actual)`,
useful as a model-free sanity signal.

> See also: [docs/awaqi-max.md](awaqi-max.md) for the agentic Awaqi Max mode.
> Both `basic` and `awaqi_max` assistants can be benchmarked across all three
> retrieval modes below with `--assistant both`.

## Retrieval modes (for benchmarking)

The runner can swap retrieval strategy to isolate which optimisation matters:

| Mode | Semantics | Simulates |
| --- | --- | --- |
| `optimized` | Hybrid (vector + BM25) fused with RRF, Gemini Amharic-aware embeddings, NLU query bias | Current production |
| `dense_only` | Vector search only | "What if we drop the keyword/BM25 layer?" |
| `bm25_only` | BM25 only | "What if we drop the Amharic-optimized embedding?" |

Compare the three to attribute quality improvements to either the embedding
or the keyword layer.

## Benchmark dataset

[`data/evaluations/benchmark.json`](../data/evaluations/benchmark.json) — 23
Amharic Q&A pairs curated from
[`kb/evaluaiton-question-and-answer`](../kb/evaluaiton-question-and-answer),
covering:

- Federal Income Tax Regulation No. **410/2017** (tax residence, fringe
  benefits, exempt benefits, taxpayer categories, donation deductions, rental
  income, withholding tax, permanent establishment)
- Income Tax (Amendment) Proclamation No. **1395/2017 / 2025** (Category A vs
  B, salary tax slabs, digital content creation, rental tax rates,
  non-resident digital services)

Each item carries:
- the question (Amharic)
- the expected answer (Amharic)
- `ground_truth.proclamation_number` and `article_numbers` (used as retrieval
  ground truth for Precision@k / Recall@k / MRR / NDCG)
- `keywords` (handy for debugging mode comparisons)

To extend the benchmark, edit the JSON file and re-run.

## How to run

### Prerequisites

- PostgreSQL with `pgvector` reachable (uses your normal `.env`)
- Documents already ingested into `documents` + `document_chunks` (so
  retrieval has something to find)
- `GOOGLE_API_KEY` set (for Gemini embeddings + the LLM judge); without it the
  judge step is skipped automatically and scores stay at 0

### Generate runs

```bash
# Run the current production pipeline
uv run --package api python scripts/run_evaluation.py --mode optimized --k 10

# Or run all three modes back-to-back for a clean comparison
uv run --package api python scripts/run_evaluation.py --mode all --k 10

# Faster smoke-test (no LLM judge, no semantic similarity embeddings)
uv run --package api python scripts/run_evaluation.py --mode optimized \
    --no-judge --no-semantic-sim --verbose
```

Each run writes a JSON file to `data/evaluations/runs/<mode>-<timestamp>.json`.

### CLI flags

| Flag | Default | Notes |
| --- | --- | --- |
| `--mode` | `optimized` | One of `optimized`, `dense_only`, `bm25_only`, `all` |
| `--k` | `10` | Top-k cutoff for retrieval metrics |
| `--benchmark` | `data/evaluations/benchmark.json` | Path to dataset |
| `--output-dir` | `data/evaluations/runs` | Where run JSON lands |
| `--no-judge` | off | Skip the LLM judge (free + fast) |
| `--no-semantic-sim` | off | Skip embedding-based answer similarity |
| `--verbose` | off | Per-item logging |

### View results

1. Start the API and web app (`make dev`).
2. Open **Admin → Evaluation** (`/admin/evaluation`).
3. Pick a run from the dropdown. The page shows:
   - aggregate retrieval + judge metrics
   - per-question table with **Question / Expected / Actual / Score (1–10)**
   - click a row to expand per-metric breakdown, retrieved proclamation
     matches, and the full answer text + judge rationale

The admin endpoints are:
- `GET /v1/admin/evaluation/runs` – run summaries
- `GET /v1/admin/evaluation/runs/{run_id}` – per-question details
- `GET /v1/admin/evaluation/benchmark` – raw benchmark dataset

## Interpreting results

The headline numbers to compare across modes are:

- **`avg_judge_overall`** — single 1–10 number for end-to-end answer quality
- **`avg_ndcg_at_k`** — best retrieval metric to track over time
- **`avg_recall_at_k`** — if this is low, generation can't be saved

Typical pattern: `bm25_only` should win on Amharic exact-term questions (e.g.
proclamation numbers, formula-style questions) and lose on paraphrased/
semantic questions; `dense_only` should be the inverse; `optimized` should
match or beat both. If `optimized` doesn't beat both baselines, the RRF
fusion or query bias is regressing — investigate before any further
optimisation.

## Files added

- [`data/evaluations/benchmark.json`](../data/evaluations/benchmark.json) – curated dataset
- [`packages/ai-engine/src/ai_engine/evaluation/`](../packages/ai-engine/src/ai_engine/evaluation/) – Python module (dataset / metrics / judge / runner)
- [`scripts/run_evaluation.py`](../scripts/run_evaluation.py) – CLI
- [`apps/api/routers/evaluation.py`](../apps/api/routers/evaluation.py) – admin API
- [`apps/web/app/[locale]/(admin)/admin/evaluation/page.tsx`](../apps/web/app/[locale]/(admin)/admin/evaluation/page.tsx) – admin UI
- Sidebar link in [`apps/web/components/admin/Sidebar.tsx`](../apps/web/components/admin/Sidebar.tsx)
