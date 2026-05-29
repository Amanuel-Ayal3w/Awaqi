# Things to Update After Real Run

This file lists every number in `technical_documentation.md` that is currently an **educated estimate**. Replace each one with a measured value after running the benchmarks against the production deployment.

The estimates are based on local profiling on the staging EC2 box and the team's eyeball during demos. They are reasonable starting points, not real measurements.

---

## How to Re-measure

1. **Performance numbers** — run `wrk -t4 -c100 -d60s` against `/v1/chat/send` and `/health` from a host with low-latency network to the EC2 instance. Use `psrecord` on the API container to capture CPU and memory. Use `pgbench` against `awaqi_db` for raw database throughput.
2. **AI accuracy numbers** — run `scripts/run_evaluation.py --assistant both --mode optimized,dense_only,bm25_only` against the current production index. The runner writes results to `data/evaluations/runs/`.
3. **Test counts** — run `make test` and `make test-web` and read the totals out of the pytest / Vitest summary lines.
4. **Security counts** — re-run the prompt-injection corpus (`tests/security/prompt_injection_corpus.json` — to be added), the OWASP ZAP scan, and `sqlmap` against the staging deployment with `--batch --crawl=2`.

After re-measuring, update the right column in each table below, then update the same numbers in `technical_documentation.md`.

---

## Section 12.5 — Test Results

Replace the test counts with the values printed by `make test` and `make test-web`. The numbers in the doc are best-effort recollections from the last green CI run.

| Field | Estimated | Measured |
|---|---|---|
| Python unit test count | 42 | TODO |
| Python integration test count | 18 | TODO |
| Frontend Vitest count | 9 | TODO |
| Playwright E2E spec count | 3 | TODO |
| CI runtime — Python unit | ~90 s | TODO |
| CI runtime — Python integration | ~3 min | TODO |
| CI runtime — web suite | ~2 min | TODO |

---

## Section 13.1 — Security Validation

Re-run the prompt-injection corpus and the OWASP ZAP scan against staging. The "mitigated" counts are the team's best estimate after manual testing during development.

| Field | Estimated | Measured |
|---|---|---|
| Prompt injection — retrieval poisoning (passes) | 28/30 | TODO |
| Prompt injection — user-supplied (passes) | 38/40 | TODO |
| SQL injection — sqlmap findings | 0 | TODO |
| XSS — reflected (Burp) findings | 0 | TODO |
| XSS — stored (announcements) findings | 0 | TODO |
| Admin endpoint access control checks | 12 endpoints, 100% blocked | TODO |
| Guest session-token tamper tests | 100% blocked | TODO |
| Rate-limit burst test | 15 pass / rest 429 | TODO |
| `securityheaders.com` grade | A | TODO |

---

## Section 13.2 — Performance Validation

All response-time and throughput numbers should be replaced after a real load run on production data volumes. Gemini-bound latencies will swing the most.

| Field | Estimated | Measured |
|---|---|---|
| AI response time — p50 | ~3.2 s | TODO |
| AI response time — p95 | ~6.4 s | TODO |
| Extractive fallback latency | ~0.4 s | TODO |
| Concurrent users — sustained | 120 | TODO |
| Concurrent users — burst | 180 | TODO |
| `/v1/chat/send` throughput | ~22 req/s | TODO |
| `/health` throughput | ~3 800 req/s | TODO |
| Cold dense-retrieval DB time | ~85 ms | TODO |
| FTS query time | ~32 ms | TODO |
| Hybrid retrieval total | ~140 ms | TODO |
| Single-query embedding latency | ~480 ms | TODO |
| 10-page PDF ingestion | ~12 s | TODO |
| 10-page OCR ingestion | ~62 s | TODO |
| CPU under load (120 conc.) | ~58% | TODO |
| Memory steady-state | ~1.4 GB | TODO |
| Redis memory | ~28 MB | TODO |

**Note.** Gemini round-trip latency is the dominant factor in the chat path. Re-measurement from the EC2 host (`eu-north-1`) may differ meaningfully from local Addis Ababa or Nairobi numbers due to network distance to Google's regional endpoint.

---

## Section 13.3 — AI Accuracy Validation

Run `scripts/run_evaluation.py` against the current production index, then drop in the headline numbers from the run report. The 23-item Amharic benchmark in `data/evaluations/benchmark.json` is the source of truth.

| Field | Estimated | Measured |
|---|---|---|
| Hit@5 (production hybrid) | ~0.91 | TODO |
| Hit@5 (dense only) | ~0.78 | TODO |
| Hit@5 (BM25 only) | ~0.74 | TODO |
| MRR (production hybrid) | ~0.78 | TODO |
| NDCG@5 (production hybrid) | ~0.81 | TODO |
| Faithfulness (basic, judge avg /10) | ~8.4 | TODO |
| Faithfulness (Awaqi Max, /10) | ~8.7 | TODO |
| Answer relevance (basic, /10) | ~8.3 | TODO |
| Context recall (basic, /10) | ~7.9 | TODO |
| Correctness (basic, /10) | ~7.8 | TODO |
| Overall weighted (basic, /10) | ~8.1 | TODO |
| Multilingual parity (am vs en, MRR gap) | ~3.2% | TODO |
| Hallucination rate (manual sample n=50) | ~3% | TODO |
| Citation accuracy (manual review) | ~96% | TODO |

**Notes for the reviewer.**

- The English-side numbers depend on whether the benchmark is mirrored. We currently only have the Amharic set; multilingual parity is a side-by-side run of the same regulation but with translated queries. If the English mirror is not yet populated, leave parity as TODO.
- The "hallucination rate" is a manual sample. Pick 50 random responses from the last week of production traffic, blind-grade against the retrieved chunks, and count any factual claim not supported by retrieval.

---

## Section 16 — Cost

Confirm against the actual AWS billing console and the Gemini usage dashboard.

| Field | Estimated | Measured |
|---|---|---|
| EC2 monthly | ~ $30 | TODO |
| EBS monthly | ~ $3 | TODO |
| S3 monthly | < $1 | TODO |
| Gemini monthly | $10 – $25 | TODO |
| GeezSMS monthly | ~ $5 | TODO |
| **Total monthly** | $50 – $65 | TODO |

---

## Process for Updating This File

When you re-measure:

1. Fill in the `Measured` column in each table above.
2. Copy the measured values into the corresponding tables in `technical_documentation.md`.
3. Delete the "(estimated)" hedging in the prose around each table.
4. Update the timestamp below.

**Last updated:** 2026-05-28 — all values estimated.
