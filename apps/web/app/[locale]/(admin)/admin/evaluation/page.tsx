"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { adminApi } from "@/lib/api"
import type {
    AssistantMode,
    EvaluationMode,
    EvaluationResultItem,
    EvaluationRunDetail,
    EvaluationRunSummary,
} from "@/types/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { RefreshCw, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

function fmtNum(n: number | null | undefined, digits = 3): string {
    if (n === null || n === undefined || Number.isNaN(n)) return "—"
    return n.toFixed(digits)
}

function fmtScore(n: number | null | undefined): string {
    if (n === null || n === undefined || Number.isNaN(n)) return "—"
    return `${n.toFixed(1)}/10`
}

function fmtMs(n: number | null | undefined): string {
    if (n === null || n === undefined) return "—"
    return `${Math.round(n)} ms`
}

function modeBadge(mode: EvaluationMode | null | undefined) {
    if (!mode) return null
    const colour =
        mode === "optimized"
            ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
            : mode === "dense_only"
              ? "bg-blue-500/10 text-blue-600 border-blue-500/30"
              : "bg-amber-500/10 text-amber-700 border-amber-500/30"
    const label =
        mode === "optimized"
            ? "Optimized (hybrid + Amharic emb.)"
            : mode === "dense_only"
              ? "Dense-only (no keyword)"
              : "BM25-only (no embedding)"
    return (
        <Badge variant="outline" className={cn("font-normal", colour)}>
            {label}
        </Badge>
    )
}

function assistantBadge(asst: AssistantMode | null | undefined) {
    const mode = asst ?? "basic"
    const colour =
        mode === "awaqi_max"
            ? "bg-violet-500/10 text-violet-600 border-violet-500/30"
            : "bg-slate-500/10 text-slate-600 border-slate-500/30"
    const label = mode === "awaqi_max" ? "Awaqi Max (ReAct)" : "Basic"
    return (
        <Badge variant="outline" className={cn("font-normal", colour)}>
            {label}
        </Badge>
    )
}

function scoreClass(score: number): string {
    if (score >= 8) return "text-emerald-600 font-semibold"
    if (score >= 5) return "text-amber-600 font-semibold"
    if (score > 0) return "text-red-600 font-semibold"
    return "text-muted-foreground"
}

export default function AdminEvaluationPage() {
    const [runs, setRuns] = useState<EvaluationRunSummary[]>([])
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
    const [detail, setDetail] = useState<EvaluationRunDetail | null>(null)
    const [loadingList, setLoadingList] = useState(true)
    const [loadingDetail, setLoadingDetail] = useState(false)
    const [refreshing, setRefreshing] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [expandedRow, setExpandedRow] = useState<string | null>(null)

    const loadRuns = useCallback(async () => {
        setRefreshing(true)
        setError(null)
        try {
            const result = await adminApi.listEvaluationRuns()
            setRuns(result.runs)
            if (result.runs.length > 0 && !selectedRunId) {
                setSelectedRunId(result.runs[0].run_id)
            }
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load evaluation runs")
        } finally {
            setLoadingList(false)
            setRefreshing(false)
        }
    }, [selectedRunId])

    const loadDetail = useCallback(async (runId: string) => {
        setLoadingDetail(true)
        setError(null)
        try {
            const d = await adminApi.getEvaluationRun(runId)
            setDetail(d)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load run detail")
            setDetail(null)
        } finally {
            setLoadingDetail(false)
        }
    }, [])

    useEffect(() => {
        void loadRuns()
    }, [loadRuns])

    useEffect(() => {
        if (selectedRunId) {
            void loadDetail(selectedRunId)
        } else {
            setDetail(null)
        }
    }, [selectedRunId, loadDetail])

    const summaryStats = useMemo(() => {
        if (!detail) return null
        const s = detail.summary
        const k = s.k ?? 10
        const stats = [
            { label: "Judge overall", value: fmtScore(s.avg_judge_overall) },
            { label: "Faithfulness", value: fmtScore(s.avg_judge_faithfulness ?? null) },
            { label: "Answer relevance", value: fmtScore(s.avg_judge_answer_relevance ?? null) },
            { label: "Context recall", value: fmtScore(s.avg_judge_context_recall ?? null) },
            { label: "Correctness", value: fmtScore(s.avg_judge_correctness ?? null) },
            { label: `Hit@${k}`, value: fmtNum(s.avg_hit_at_k) },
            { label: `Precision@${k}`, value: fmtNum(s.avg_precision_at_k) },
            { label: `Recall@${k}`, value: fmtNum(s.avg_recall_at_k) },
            { label: "MRR", value: fmtNum(s.avg_mrr) },
            { label: `NDCG@${k}`, value: fmtNum(s.avg_ndcg_at_k) },
            { label: "Semantic sim.", value: fmtNum(s.avg_semantic_similarity) },
            { label: "Avg latency", value: fmtMs(s.avg_latency_ms) },
        ]
        if ((s.assistant_mode ?? "basic") === "awaqi_max") {
            const tc = s.avg_agent_tool_calls
            const wp = s.pct_agent_used_web_search
            stats.push(
                {
                    label: "Avg tool calls",
                    value: tc === null || tc === undefined ? "—" : tc.toFixed(2),
                },
                {
                    label: "Used web search",
                    value:
                        wp === null || wp === undefined
                            ? "—"
                            : `${Math.round(wp * 100)}%`,
                },
            )
        }
        return stats
    }, [detail])

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">RAG Evaluation</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Benchmark runs from <code className="font-mono text-xs">scripts/run_evaluation.py</code>.
                        Compare retrieval modes (optimized hybrid vs. dense-only vs. BM25-only)
                        and review the LLM-as-judge score per question.
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void loadRuns()}
                    disabled={refreshing}
                >
                    <RefreshCw className={cn("mr-2 h-4 w-4", refreshing && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {error && (
                <Card className="border-destructive/50">
                    <CardContent className="flex items-center gap-2 pt-6 text-destructive">
                        <AlertCircle className="h-4 w-4" />
                        <span className="text-sm">{error}</span>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base">Runs</CardTitle>
                </CardHeader>
                <CardContent>
                    {loadingList ? (
                        <p className="text-sm text-muted-foreground">Loading…</p>
                    ) : runs.length === 0 ? (
                        <div className="text-sm text-muted-foreground">
                            No runs yet. Generate one with:
                            <pre className="mt-2 overflow-x-auto rounded-md bg-muted p-3 text-xs">
{`# Compare basic vs awaqi_max across all 3 retrieval modes
uv run --package api python scripts/run_evaluation.py \\
    --mode all --assistant both --k 10`}
                            </pre>
                        </div>
                    ) : (
                        <div className="flex flex-wrap items-center gap-3">
                            <Select
                                value={selectedRunId ?? undefined}
                                onValueChange={(v) => setSelectedRunId(v)}
                            >
                                <SelectTrigger className="w-[420px]">
                                    <SelectValue placeholder="Pick a run" />
                                </SelectTrigger>
                                <SelectContent>
                                    {runs.map((r) => (
                                        <SelectItem key={r.run_id} value={r.run_id}>
                                            {r.run_id} · {r.assistant_mode ?? "basic"} ·{" "}
                                            {r.mode ?? "?"} · overall{" "}
                                            {fmtScore(r.avg_judge_overall)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {detail && assistantBadge(detail.summary.assistant_mode ?? "basic")}
                            {detail && modeBadge(detail.summary.mode)}
                            <span className="text-xs text-muted-foreground">
                                {detail?.summary.total_questions ?? 0} questions ·{" "}
                                {detail?.summary.benchmark ?? "—"}
                            </span>
                        </div>
                    )}
                </CardContent>
            </Card>

            {summaryStats && (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">Aggregate metrics</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                            {summaryStats.map((s) => (
                                <div
                                    key={s.label}
                                    className="rounded-lg border bg-card p-3"
                                >
                                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                        {s.label}
                                    </div>
                                    <div className="mt-1 text-lg font-semibold tabular-nums">
                                        {s.value}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base">Per-question results</CardTitle>
                </CardHeader>
                <CardContent>
                    {loadingDetail ? (
                        <p className="text-sm text-muted-foreground">Loading…</p>
                    ) : !detail ? (
                        <p className="text-sm text-muted-foreground">Select a run.</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                                        <th className="py-2 pr-3 w-[34%]">Question</th>
                                        <th className="py-2 pr-3 w-[28%]">Expected</th>
                                        <th className="py-2 pr-3 w-[28%]">Actual</th>
                                        <th className="py-2 pr-3 text-right">Score</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {detail.results.map((r) => (
                                        <EvalRow
                                            key={r.item_id}
                                            row={r}
                                            k={detail.summary.k ?? 10}
                                            expanded={expandedRow === r.item_id}
                                            onToggle={() =>
                                                setExpandedRow(
                                                    expandedRow === r.item_id ? null : r.item_id
                                                )
                                            }
                                        />
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}

function EvalRow({
    row,
    k,
    expanded,
    onToggle,
}: {
    row: EvaluationResultItem
    k: number
    expanded: boolean
    onToggle: () => void
}) {
    return (
        <>
            <tr
                className="border-b align-top transition-colors hover:bg-muted/40 cursor-pointer"
                onClick={onToggle}
            >
                <td className="py-3 pr-3">
                    <div className="font-medium">{row.question}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                        <code className="font-mono">{row.item_id}</code> · {row.topic} ·{" "}
                        {row.language}
                    </div>
                </td>
                <td className="py-3 pr-3 text-xs text-muted-foreground">
                    {row.expected_answer.length > 240
                        ? row.expected_answer.slice(0, 240) + "…"
                        : row.expected_answer}
                </td>
                <td className="py-3 pr-3 text-xs">
                    {row.actual_answer.length > 240
                        ? row.actual_answer.slice(0, 240) + "…"
                        : row.actual_answer}
                </td>
                <td className="py-3 pr-3 text-right">
                    <div className={cn("text-lg tabular-nums", scoreClass(row.judge_overall))}>
                        {row.judge_overall ? row.judge_overall.toFixed(0) : "—"}
                        <span className="text-xs text-muted-foreground">/10</span>
                    </div>
                </td>
            </tr>
            {expanded && (
                <tr className="border-b bg-muted/30">
                    <td colSpan={4} className="px-3 py-4">
                        <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
                            <ScoreCell label="Faithfulness" value={row.judge_faithfulness} suffix="/10" />
                            <ScoreCell label="Answer relevance" value={row.judge_answer_relevance} suffix="/10" />
                            <ScoreCell label="Context recall" value={row.judge_context_recall} suffix="/10" />
                            <ScoreCell label="Correctness" value={row.judge_correctness} suffix="/10" />
                            <ScoreCell label={`Hit@${k}`} value={row.hit_at_k} digits={2} />
                            <ScoreCell label={`Precision@${k}`} value={row.precision_at_k} digits={3} />
                            <ScoreCell label={`Recall@${k}`} value={row.recall_at_k} digits={3} />
                            <ScoreCell label="MRR" value={row.mrr} digits={3} />
                            <ScoreCell label={`NDCG@${k}`} value={row.ndcg_at_k} digits={3} />
                            <ScoreCell label="Semantic sim." value={row.semantic_similarity} digits={3} />
                            <ScoreCell label="Latency" value={row.latency_ms} digits={0} suffix=" ms" />
                            <div className="rounded-lg border bg-card p-3">
                                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                    Retrieved
                                </div>
                                <div className="mt-1 text-xs font-mono break-all">
                                    {row.retrieved_proclamations
                                        .map((p, i) => `${p ?? "?"}${row.relevant_mask[i] ? "✓" : ""}`)
                                        .join(", ") || "—"}
                                </div>
                            </div>
                        </div>
                        {row.judge_rationale && (
                            <div className="mt-4 rounded-lg border bg-card p-3 text-xs">
                                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                    Judge rationale
                                </div>
                                <div className="mt-1">{row.judge_rationale}</div>
                            </div>
                        )}
                        <details className="mt-4 text-xs">
                            <summary className="cursor-pointer text-muted-foreground">
                                Full expected vs actual
                            </summary>
                            <div className="mt-2 grid gap-3 lg:grid-cols-2">
                                <div className="rounded-md border bg-card p-3">
                                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                        Expected
                                    </div>
                                    <div className="mt-1 whitespace-pre-wrap">{row.expected_answer}</div>
                                </div>
                                <div className="rounded-md border bg-card p-3">
                                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                        Actual
                                    </div>
                                    <div className="mt-1 whitespace-pre-wrap">{row.actual_answer}</div>
                                </div>
                            </div>
                        </details>
                    </td>
                </tr>
            )}
        </>
    )
}

function ScoreCell({
    label,
    value,
    digits = 1,
    suffix = "",
}: {
    label: string
    value: number
    digits?: number
    suffix?: string
}) {
    return (
        <div className="rounded-lg border bg-card p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {label}
            </div>
            <div className="mt-1 text-base font-semibold tabular-nums">
                {value === null || value === undefined || Number.isNaN(value)
                    ? "—"
                    : `${value.toFixed(digits)}${suffix}`}
            </div>
        </div>
    )
}
