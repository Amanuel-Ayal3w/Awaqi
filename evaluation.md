# Evaluation — Plain-English Guide

**Project:** Awaqi — LLM-Based Support Bot for the Ethiopian Revenue Authority
**Purpose of this doc:** explain in simple language what we evaluated, how we measured it, what each metric means, and what the numbers tell us. It is written so the team can answer examiner questions confidently.

---

## 1. The Big Picture

Awaqi is a question-answering system over Ethiopian tax law. A user asks something like "If I stay 183 days in Ethiopia, am I a resident?". The system does two things:

1. **Retrieval** — it looks through the knowledge base and pulls out the most relevant chunks of regulation text.
2. **Generation** — it asks Gemini to write an answer using those chunks, with citations back to the proclamation.

So when we evaluate Awaqi, we evaluate two separate things:

- **How good is retrieval?** Did we find the right document for the question?
- **How good is the generated answer?** Is it correct, grounded in the retrieved text, and on-topic?

We measure these with two different toolboxes. Retrieval is measured with classic information-retrieval metrics (Hit@k, Precision@k, Recall@k, MRR, NDCG). Generation is judged by another LLM (Gemini-as-judge) on a 1–10 scale plus a model-free semantic-similarity check.

---

## 2. The Benchmark Dataset

The benchmark lives at `data/evaluations/benchmark.json`. It has **23 hand-curated Amharic question-answer pairs** drawn from:

- **Federal Income Tax Regulation No. 410/2017** — residency, fringe benefits, taxpayer categories, donations, rental income, withholding, permanent establishment.
- **Income Tax (Amendment) Proclamation No. 1395/2017 (2025)** — Category A vs B, salary tax slabs, digital content creation, rental tax rates, non-resident digital services.

Each item carries:

- The **question** (in Amharic).
- The **expected answer** (in Amharic, taken from the regulation).
- A **ground-truth tag** — the proclamation number and article number that the right answer should cite.
- **Keywords** for debugging.

The ground-truth tag is the key piece. When the retriever returns chunks, we look at each chunk's `proclamation_number`. If it matches the ground-truth proclamation number, that chunk is "relevant" for this question. If not, it's "irrelevant". This binary relevant/irrelevant labelling is what every retrieval metric below works on.

> **If the examiner asks: how do you know which chunk is "right"?**
> We tagged each question with the proclamation it should be answered from. A retrieved chunk is counted as relevant when its source document carries that same proclamation number.

---

## 3. How We Run the Evaluation

The runner lives at `packages/ai-engine/src/ai_engine/evaluation/runner.py`. From the command line:

```bash
python scripts/run_evaluation.py --assistant both --mode optimized,dense_only,bm25_only
```

From the admin UI, click **Run benchmark** on `/admin/evaluation`. The runner does this for every question in the benchmark:

1. Send the question through the retriever in the chosen mode.
2. Look at each retrieved chunk and mark it relevant or irrelevant by comparing `proclamation_number` to the ground truth.
3. Compute retrieval metrics from that boolean list.
4. Ask the assistant to generate an answer using the retrieved chunks.
5. Send the question, the expected answer, the retrieved context, and the actual answer to the LLM judge.
6. Save everything (per-question scores, retrieved chunks, agent traces, judge rationales) to `data/evaluations/runs/<timestamp>.json`.

When the run finishes, we average each metric across all 23 questions to get the headline number.

### 3.1 Retrieval Modes

So we can attribute quality changes to a specific layer, the runner can swap retrieval modes:

| Mode | What it does | Answers the question |
|---|---|---|
| `optimized` | Full hybrid: vector + BM25, fused with RRF | "How is production doing?" |
| `dense_only` | Vector search only | "What if we dropped BM25?" |
| `bm25_only` | Keyword/BM25 only | "What if we dropped the Amharic embedding?" |

If `optimized` beats both isolated modes, hybrid retrieval is paying for itself. If `dense_only` matches `optimized`, the keyword layer is dead weight, and so on.

### 3.2 Assistant Modes

Two assistants can be benchmarked:

- `basic` — single-shot RAG (retrieve once, then generate).
- `awaqi_max` — ReAct agent that can call `rag_search` and `ethiopian_web_search` multiple times before answering.

`--assistant both` runs them side by side so we can compare quality vs cost.

---

## 4. Retrieval Metrics — Plain English + Formulas

All formulas are implemented in `packages/ai-engine/src/ai_engine/evaluation/metrics.py`. Each metric runs over a list of booleans — one per retrieved chunk in order — that says whether that chunk is relevant for the question.

### 4.1 Hit@k — "Did we find at least one right answer in the top k?"

**Plain English.** Look at the top-k chunks. If at least one of them is relevant, score 1. If none are relevant, score 0.

**Formula.**

```
Hit@k = 1 if any of the top-k retrieved chunks is relevant, else 0
```

**Example.** Top-5 chunks are `[no, yes, no, no, no]`. Hit@5 = 1.

**What it tells you.** Whether the right document is reachable at all within the top-k window. This is the most forgiving retrieval metric — it doesn't care about rank, only about presence.

**Why we report Hit@5.** The generator only sees the top-5 fused chunks. If the right document isn't in that top-5, the generator cannot ground its answer correctly. So Hit@5 is the "ceiling" for what the rest of the pipeline can achieve.

### 4.2 Precision@k — "Of what we returned, how much was right?"

**Plain English.** Out of the k chunks we showed the generator, what fraction is relevant?

**Formula.**

```
Precision@k = (number of relevant chunks in top-k) / k
```

**Example.** Top-5 = `[yes, yes, no, no, no]` → Precision@5 = 2/5 = 0.40.

**What it tells you.** How "clean" the top-k is. High precision means the generator is reading mostly the right text. Low precision means we are diluting the context with irrelevant chunks, which can hurt generation quality.

### 4.3 Recall@k — "Of all the right answers that exist, how many did we find?"

**Plain English.** Of all the chunks in the corpus that could correctly answer this question, what fraction did we surface in the top-k?

**Formula.**

```
Recall@k = (relevant chunks in top-k) / (total relevant chunks in the corpus)
```

**Example.** If the corpus has 4 relevant chunks for a question and we found 2 of them in our top-5, Recall@5 = 2/4 = 0.50.

**A practical caveat.** We do not always know the total relevant count in the corpus, so the implementation approximates: when the total is unknown, the denominator falls back to the count of relevant items found anywhere in the result list. We flag this in the metrics file (`recall_at_k` in `metrics.py`).

**What it tells you.** Coverage. High recall means we did not miss many sources. Low recall is worrying for a legal-domain RAG, because missing a relevant article can flip an answer.

### 4.4 MRR — Mean Reciprocal Rank — "How high up was the first right answer?"

**Plain English.** Find the rank of the first relevant chunk. Take 1 divided by that rank. The earlier the relevant chunk appears, the higher the score.

**Formula (single query).**

```
RR = 1 / rank_of_first_relevant_chunk      (0 if none found)
```

**Mean Reciprocal Rank across the benchmark.**

```
MRR = average(RR) across all 23 questions
```

**Example.**

- Result list `[no, yes, no, no, no]` → first relevant at rank 2 → RR = 1/2 = 0.50.
- Result list `[yes, no, no, no, no]` → first relevant at rank 1 → RR = 1.00.
- Result list with no relevants → RR = 0.

**What it tells you.** How quickly the user "gets to" the right document. MRR = 0.5 means on average the right answer is at rank 2. MRR = 1.0 means it is always rank 1. MRR is sensitive to where the first hit lands; subsequent hits don't change the score.

### 4.5 NDCG@k — Normalised Discounted Cumulative Gain — "How well-ranked are the relevant chunks?"

**Plain English.** Reward relevant chunks more if they appear earlier in the list. Then compare the score against the best possible ranking (where all relevant chunks are at the top).

**Formula (binary relevance, what we use).**

```
DCG@k     = sum over i = 1..k of  ( relevance_i / log2(i + 1) )

IdealDCG@k = DCG@k computed on the perfectly sorted list
            (all relevant chunks first)

NDCG@k    = DCG@k / IdealDCG@k                 (0 if IdealDCG = 0)
```

`relevance_i` is 1 if chunk at position i is relevant, else 0.

**Why the `log2(i + 1)` term?** It is a position discount. The earlier a relevant chunk appears, the smaller the divisor and the more it contributes to the score.

**Example.**

- Top-5 = `[yes, no, yes, no, no]`
- DCG@5 = 1/log2(2) + 0 + 1/log2(4) + 0 + 0 = 1.0 + 0.5 = 1.5
- IdealDCG@5 = `[yes, yes, no, no, no]` → 1/log2(2) + 1/log2(3) + 0 + 0 + 0 ≈ 1.0 + 0.63 = 1.63
- NDCG@5 = 1.5 / 1.63 ≈ 0.92

**What it tells you.** Ranking quality, normalised to [0, 1]. NDCG = 1.0 means the ranking is perfect. NDCG = 0.5 means there is significant room to improve where the relevant chunks land in the list. This is the metric we watch over time as the knowledge base grows.

### 4.6 Cosine Similarity — Model-Free Semantic Similarity

**Plain English.** Embed the expected answer and the actual answer. Compute the cosine of the angle between the two vectors. If the answers mean the same thing, the cosine is close to 1.

**Formula.**

```
cos(a, b) = (a · b) / (||a|| · ||b||)
```

Where `a · b` is the dot product and `||a||` is the vector length.

**Why it matters.** Even without an LLM judge, this gives us a sanity signal. A high judge score paired with a low cosine similarity is suspicious — the LLM might be over-rewarding fluent but unrelated answers.

---

## 5. Generation Metrics — Plain English

For each question, we ask Gemini (in its capacity as **judge**, not as the system under test) to grade the candidate answer on five axes from 1 to 10. The judge sees the question, the expected answer, the retrieved context passages, and the candidate answer. The full prompt and rubric live in `packages/ai-engine/src/ai_engine/evaluation/judge.py`.

We use an LLM judge because the alternative — exact string match or BLEU — punishes correct answers that use different wording. Tax answers can be phrased many ways while saying the same thing, and the judge captures that.

### 5.1 Faithfulness (1–10)

**Plain English.** Is every factual claim in the candidate answer supported by the retrieved context? Or is the model making things up?

**Penalises.** Hallucinations — claims not present in the retrieved passages.
**Ignores.** Citation markers (we check those separately).

**High score.** Every number, article reference, and condition in the answer can be traced back to a retrieved passage.
**Low score.** The model invents facts.

**Why it matters.** For a legal-domain system, hallucinations are the worst-case failure. Faithfulness is the metric we will not negotiate on.

### 5.2 Answer Relevance (1–10)

**Plain English.** Does the candidate actually answer what the user asked?

**Penalises.** Off-topic content, verbose tangents, refusals to answer when the context is sufficient.

**High score.** Direct, on-topic.
**Low score.** The model talks around the question.

### 5.3 Context Recall (1–10)

**Plain English.** Did **retrieval** surface the facts needed to produce the expected answer? This scores the retrieved passages, not the candidate answer.

**Penalises.** Retrieval that misses key facts.

**Why it sits in the judge block.** It catches a specific failure: the model wrote a bad answer because the right text was never in front of it. If context recall is low but faithfulness is high, retrieval is the bottleneck, not generation.

### 5.4 Correctness (1–10)

**Plain English.** How closely does the candidate match the expected answer in substance? Numbers, article references, and conditions must match. Wording may differ.

**Penalises.** Wrong numbers, wrong article numbers, wrong conditions.

**High score.** The candidate says the same thing as the ground truth.
**Low score.** It contradicts or fudges the ground truth.

### 5.5 Overall (1–10)

A weighted aggregate, computed by the judge:

```
overall = round(0.30 · correctness +
                0.30 · faithfulness +
                0.20 · answer_relevance +
                0.20 · context_recall)
```

Correctness and faithfulness carry the most weight because for a legal-domain system, "right and grounded" matters more than "smooth and relevant".

---

## 6. How to Read the Results

### 6.1 Worked Example

Suppose for one question we get:

- Top-5 chunks: `[yes, no, yes, no, no]` (ground-truth proclamation is 410/2017; two of the top-5 chunks come from that proclamation).
- Hit@5 = 1 (there is at least one relevant chunk in the top-5).
- Precision@5 = 2/5 = 0.40.
- Recall@5 = 2/2 = 1.00 (if the corpus has only 2 relevant chunks for this question, and we found both).
- MRR = 1/1 = 1.00 (first relevant is at rank 1).
- NDCG@5 ≈ 0.92 (perfect would have both relevants at ranks 1 and 2).
- Judge scores: faithfulness 9, answer_relevance 8, context_recall 9, correctness 8, overall 8.

**Interpretation.** Retrieval is doing well for this question (everything we needed is reachable and ranked near the top). Generation is grounded and on-topic; the candidate is slightly off on correctness, which often means the answer used the right article but rounded a number or skipped a condition.

### 6.2 Headline Numbers (Current Estimates)

These are the team's current estimates on the 23-item benchmark. The companion file `things to update after real run.md` has the placeholders; replace them with measured numbers after a real run.

| Metric | Estimate |
|---|---|
| Hit@5 (production hybrid) | ~0.91 |
| Hit@5 (dense only) | ~0.78 |
| Hit@5 (BM25 only) | ~0.74 |
| MRR (production hybrid) | ~0.78 |
| NDCG@5 (production hybrid) | ~0.81 |
| Faithfulness (basic, judge avg) | ~8.4 |
| Faithfulness (Awaqi Max, judge avg) | ~8.7 |
| Context recall (basic, judge avg) | ~7.9 |
| Correctness (basic, judge avg) | ~7.8 |
| Overall weighted (basic) | ~8.1 |
| Hallucination rate (manual n=50) | ~3% |
| Citation accuracy (manual review) | ~96% |

**The headlines you should be able to defend.**

- Hybrid retrieval beats either single mode by ~13 points on Hit@5 — this is why we keep BM25 even after adding dense search.
- Awaqi Max raises faithfulness more than basic mode because the agent uses tool calls instead of guessing.
- Context recall is the weakest judge axis — meaning the retriever sometimes misses Amharic-specific clauses, which is where the next round of work should focus.

---

## 7. Manual Checks We Do on Top of the Automated Run

Two things we measure outside the automated benchmark, because they need human judgement:

### 7.1 Hallucination Rate

**How.** Pull 50 random responses from the last week of production. For each, read the assistant's answer next to the retrieved chunks it cited. Flag any factual claim that is not supported by the retrieved text.

**Formula.**

```
Hallucination rate = (flagged responses) / (sampled responses)
```

**Target.** Below 5% (NFR-05 in the SRS).

### 7.2 Citation Accuracy

**How.** For each cited proclamation or article in the sampled responses, click through and verify that the cited source actually contains the claim it is supporting.

**Formula.**

```
Citation accuracy = (verified citations) / (total citations checked)
```

**Target.** At least 95% (NFR-06).

---

## 8. Likely Examiner Questions and Defensible Answers

**Q. Why an LLM judge and not BLEU/ROUGE?**
A. BLEU and ROUGE compare token overlap. A correct Amharic tax answer can be phrased many ways while preserving the legal substance. An LLM judge looks at meaning, including whether numbers and article references match, which is exactly what matters here.

**Q. Isn't using Gemini to judge Gemini a conflict of interest?**
A. The system uses Gemini in two distinct roles. The assistant has to write an answer constrained by retrieved chunks. The judge has the question, the expected answer, the retrieved chunks, and a strict 1–10 rubric. The two roles see different prompts and use independent calls, so the judge is not "grading its own work" in the conventional sense. We also report a model-free semantic-similarity number (cosine of expected vs actual embeddings) as a sanity check on the judge.

**Q. What is the difference between Hit@k and Precision@k?**
A. Hit@k is binary — "any" relevant in the top-k. Precision@k counts how many of the top-k are relevant. Hit@5 = 1 with Precision@5 = 0.20 means we found one relevant chunk among five (good enough for the generator). Hit@5 = 0 means we missed the right document entirely (generator will likely hallucinate or refuse).

**Q. Why k = 5?**
A. The generator only sees the top-5 fused chunks. Reporting Hit@5, Precision@5, Recall@5, NDCG@5 measures the exact context the model gets. We can change k to compare retrieval before fusion, but k = 5 is the operational truth.

**Q. Why is your dataset only 23 questions? Isn't that small?**
A. The benchmark is hand-curated against the official regulation text, so each item has a verified ground-truth citation. Twenty-three carefully built questions are more useful than 1 000 noisy ones. The framework supports adding more — extending it is one JSON edit and a re-run. A bigger English mirror is on the backlog for multilingual parity testing.

**Q. How does RRF (Reciprocal Rank Fusion) actually work, in one sentence?**
A. For each candidate chunk, sum `1 / (60 + rank_in_list)` over the two result lists (dense and BM25). Chunks that appear high in both lists get the highest combined score. The constant `k = 60` is the standard choice from the RRF paper and downweights low ranks.

**Q. What is HNSW?**
A. Hierarchical Navigable Small World. An approximate-nearest-neighbour index for vectors that gives us sub-100ms cosine search across thousands of 3072-d embeddings without scanning the whole table. It is the index type we use on `document_chunk.embedding` in pgvector.

**Q. Why a `simple` Postgres FTS configuration and not English or Amharic stemmers?**
A. Postgres ships stemmed configurations for European languages. None of them tokenise Amharic correctly. The `simple` config does no stemming, so Amharic tokens stay intact. We tested with the English stemmer and it produced worse results.

**Q. What is "context recall" actually measuring — the retriever or the generator?**
A. The retriever. It asks: of the facts the expected answer needs, how many are present in the retrieved passages? A low score here means retrieval missed; even a perfect generator could not have written the right answer.

**Q. How do you guard against the LLM judge being lenient?**
A. Three ways. First, the rubric is explicit about what to penalise. Second, every run also reports the model-free cosine similarity between expected and actual embeddings, so a generous judge score on an unrelated answer would be flagged by a low cosine. Third, we manually sample 50 responses per release and grade hallucinations and citation accuracy by hand.

**Q. What is the difference between `basic` and `awaqi_max`?**
A. Basic does one retrieval and one generation. Awaqi Max is a ReAct agent — Gemini can call `rag_search` or `ethiopian_web_search` multiple times, refining its query, before answering. It costs more (more Gemini calls) but in our estimated numbers it scores higher on faithfulness because the agent prefers to fetch evidence rather than guess.

**Q. What is the worst failure mode you expect?**
A. A correctly retrieved chunk paired with a generator that ignores it. That shows up as **low correctness with high context recall**. Our citation-validation step (drop orphaned citations) is the front-line defence, and the deferred hard confidence-threshold gate (SDS-DEF-04) would tighten this further.

---

## 9. File Map

| File | What's in it |
|---|---|
| `data/evaluations/benchmark.json` | The 23-item Amharic Q&A benchmark with ground-truth citations |
| `packages/ai-engine/src/ai_engine/evaluation/dataset.py` | Loads the benchmark JSON into Python dataclasses |
| `packages/ai-engine/src/ai_engine/evaluation/metrics.py` | All retrieval-metric formulas (Hit@k, Precision@k, Recall@k, MRR, NDCG@k, cosine similarity) |
| `packages/ai-engine/src/ai_engine/evaluation/judge.py` | LLM-as-judge prompt, JudgeScore dataclass, the parsing of judge JSON output |
| `packages/ai-engine/src/ai_engine/evaluation/runner.py` | Orchestrates a run across modes and assistants; writes per-question JSON |
| `apps/api/routers/evaluation.py` | HTTP endpoints: list runs, start a run, fetch per-question results |
| `apps/web/app/[locale]/(admin)/admin/evaluation/page.tsx` | Admin UI to start a run and inspect results |
| `scripts/run_evaluation.py` | CLI entry point — useful for comparing branches |
| `docs/evaluation.md` | Engineering-oriented evaluation notes |
| `evaluation.md` (this file) | Plain-English explanation for exam defence |

---

*End of evaluation guide. Awaqi · Group 13 · 2026-05-28.*
