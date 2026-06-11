# Awaqi Max — agentic ReAct mode

Awaqi ships two assistant modes the end user can switch between in the chat
UI. Awaqi Max wraps the existing RAG pipeline in a Gemini-powered ReAct
(Reason → Act → Observe) loop so the assistant can iteratively refine its
KB searches and, when the knowledge base falls short, reach for an
Ethiopian-grounded public web search.

## Mode summary

| | Basic | Awaqi Max |
| --- | --- | --- |
| Pattern | Single-shot RAG | ReAct agent loop (up to 5 iterations) |
| Tools | none | `rag_search`, `ethiopian_web_search` |
| Latency | ~1 retrieval + 1 LLM call | up to N retrievals + N+1 LLM calls |
| When to use | Most questions | Multi-hop, ambiguous, very recent, or KB-miss questions |
| Default | ✅ | opt-in via the chat UI dropdown |

The dropdown selection persists per browser in
`localStorage["awaqi:assistantMode"]`. Switching is a no-op on existing
messages; it takes effect on the next send.

## ReAct loop

```
       ┌──────────────┐
USER → │   Gemini     │ ─► chooses tool
       │  (system     │      │
       │   prompt +   │      ▼
       │   tools)     │  rag_search(query)        ┌─────────┐
       └──────┬───────┘  ethiopian_web_search(q) →│ tools.py│
              ▲                                   └────┬────┘
              │     observation (JSON)                 │
              └────────────────────────────────────────┘
                    (loop ≤ MAX_ITERATIONS)
              │
              ▼  no tool call → final text
        FINAL ANSWER (cited)
```

1. The model sees the user's question, the system prompt, and the schemas
   of both tools.
2. It decides whether to call a tool. If yes, the call's `FunctionCall` is
   executed by [`packages/ai-engine/src/ai_engine/agent/react_agent.py`](../packages/ai-engine/src/ai_engine/agent/react_agent.py)
   and a `FunctionResponse` is appended to the message history.
3. Repeat until the model emits plain text or the iteration budget
   (`AWAQI_MAX_ITERATIONS`, default 5) is hit.
4. If the budget is hit without a final answer, the loop synthesises one
   from the union of retrieved chunks using the same `answer_from_chunks`
   helper as Basic mode — Awaqi Max never returns nothing.

The Gemini function-calling surface is wired with manual control instead of
the SDK's automatic function calling so we keep a full
[`AgentTrace`](../packages/ai-engine/src/ai_engine/agent/react_agent.py) that
the admin evaluation page can show step-by-step.

## Tools

Both live in [`packages/ai-engine/src/ai_engine/agent/tools.py`](../packages/ai-engine/src/ai_engine/agent/tools.py).

### `rag_search(query)`

Calls the same hybrid retriever the chat router uses (vector + BM25 fused
with RRF + NLU bias), returning the top `AWAQI_MAX_RAG_TOP_K` chunks
(default 8). The agent is told to call this **first** and to refine the
query (translate, narrow, add proclamation/article numbers) and call it
again if the first pass returns weak excerpts.

What the agent sees on each call is a JSON payload of at most 8 trimmed
excerpts (~600 chars each) — small enough to keep many iterations cheap
but enough to decide whether to refine, switch tool, or answer.

### `ethiopian_web_search(query)`

Wraps Gemini's built-in `google_search` grounding tool with a system prompt
that biases results toward Ethiopian sources:

```
mor.gov.et OR site:.et OR mof.gov.et OR mohfw.gov.et
OR fanabc.com OR ena.et OR addisstandard.com
OR ethiopianreporter.com OR walta.com
```

The agent is explicitly instructed (in `SYSTEM_INSTRUCTIONS`) to use the
web search **only when the KB cannot answer** — e.g. recent news,
circulars, deadlines, or topics not in the indexed regulations. The
returned observation includes:

- a concise factual summary (≤200 words)
- up to 8 source URIs harvested from Gemini's `grounding_metadata`

Those URIs are merged into the final response's `web_citations` and
surfaced as additional citation pills alongside the regular KB citations.

### Adding a new tool

1. Implement an `async` function that returns a JSON-serialisable
   observation dataclass.
2. Add a `types.FunctionDeclaration` to
   `gemini_function_declarations()` describing it.
3. Handle the new `tool_name` branch in the loop in
   `react_agent.py::run_awaqi_max`.

That's it — no other code needs to change.

## Wire-up

**Backend** — [`apps/api/routers/chat.py`](../apps/api/routers/chat.py)
inspects `request.mode`:

- `mode == "basic"` → existing single-shot path.
- `mode == "awaqi_max"` → calls `run_awaqi_max(...)`, persists the same
  `cited_chunks` JSON on the `Message` row, and adds two extra response
  fields:
  - `agent_trace`: list of `{step, type, tool_name, tool_args, observation, text}`
  - `web_citations`: list of `{title, uri}`

**Frontend** — [`apps/web/components/chat/ChatInterface.tsx`](../apps/web/components/chat/ChatInterface.tsx)
keeps the selected mode in state (persisted to localStorage) and threads
it through every `chatApi.send`. The selector itself is the dropdown
inside [`ChatInput.tsx`](../apps/web/components/chat/ChatInput.tsx).

**Schemas** — `apps/api/schemas.py` exposes `mode: AssistantMode = "basic"`
on `ChatRequest` and the trace fields on `ChatResponse`; the TypeScript
mirror lives in `apps/web/types/api.ts`.

## Environment

| Var | Default | Notes |
| --- | --- | --- |
| `GOOGLE_API_KEY` | — | Required. Used for both the agent's Gemini calls and the `google_search` grounding tool. Without it Awaqi Max returns a clear "unavailable" message instead of crashing. |
| `GEMINI_CHAT_MODEL` | `gemini-3.5-flash` | Same model used by Basic mode for consistency. |
| `AWAQI_MAX_ITERATIONS` | `5` | Hard cap on tool-call iterations. |
| `AWAQI_MAX_RAG_TOP_K` | `8` | Top-k chunks returned per `rag_search` call. |

## Evaluation

The benchmark runner has two independent axes now:

- `--mode` (retrieval): `optimized` | `dense_only` | `bm25_only` | `all`
- `--assistant`: `basic` | `awaqi_max` | `both`

Run both assistants across all retrieval modes and compare on
`/admin/evaluation`:

```bash
uv run --package api python scripts/run_evaluation.py \
    --mode all --assistant both --k 10
```

Each run lands in `data/evaluations/runs/<assistant>-<mode>-<timestamp>.json`.
For Awaqi Max runs the summary additionally reports:

- `avg_agent_tool_calls` — average number of tool calls per question
- `pct_agent_used_web_search` — fraction of questions where the agent
  invoked the Ethiopian web search

Retrieval metrics (`Hit@k`, `Precision@k`, `Recall@k`, `MRR`, `NDCG@k`)
under `awaqi_max` are computed against the **union** of all chunks the
agent surfaced across its tool calls — so they directly answer "did the
agent eventually retrieve the right doc?" rather than "did the first
retrieval get it?".

### What to look for when comparing modes

| Pattern | What it means |
| --- | --- |
| Awaqi Max judge-overall > Basic, similar latency | Iterating helped on ambiguous questions; ship it. |
| Awaqi Max wins on faithfulness but loses on latency | Expected: extra grounding costs LLM calls. |
| `pct_agent_used_web_search` is high but answers don't improve | The KB has the answer — tighten the agent's system prompt to discourage web search. |
| Awaqi Max worse than Basic | Either the agent is over-thinking simple questions (lower `MAX_ITERATIONS`) or the tools are returning poor evidence (inspect `agent_trace` per row). |

## Files added / changed

- New: [`packages/ai-engine/src/ai_engine/agent/`](../packages/ai-engine/src/ai_engine/agent/)
  (`__init__.py`, `tools.py`, `react_agent.py`)
- New: [`docs/awaqi-max.md`](awaqi-max.md) — this document
- Changed: [`apps/api/schemas.py`](../apps/api/schemas.py) — `mode`,
  `agent_trace`, `web_citations`
- Changed: [`apps/api/routers/chat.py`](../apps/api/routers/chat.py) — branch on `mode`
- Changed: [`apps/web/types/api.ts`](../apps/web/types/api.ts) — `AssistantMode`,
  `AgentTraceStep`, updated `ChatRequest` / `ChatResponse`
- Changed: [`apps/web/components/chat/ChatInput.tsx`](../apps/web/components/chat/ChatInput.tsx) — mode dropdown
- Changed: [`apps/web/components/chat/ChatInterface.tsx`](../apps/web/components/chat/ChatInterface.tsx) — threads mode through send
- Changed: [`packages/ai-engine/src/ai_engine/evaluation/runner.py`](../packages/ai-engine/src/ai_engine/evaluation/runner.py)
  — `assistant_mode` axis + agent-specific stats
- Changed: [`scripts/run_evaluation.py`](../scripts/run_evaluation.py) — `--assistant` flag
- Changed: [`apps/api/routers/evaluation.py`](../apps/api/routers/evaluation.py) — surfaces new fields
- Changed: [`apps/web/app/[locale]/(admin)/admin/evaluation/page.tsx`](../apps/web/app/[locale]/(admin)/admin/evaluation/page.tsx)
  — assistant-mode badge + Awaqi Max stats
