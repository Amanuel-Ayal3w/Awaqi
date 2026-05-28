"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, Database, Loader2, RefreshCw, Trash2 } from "lucide-react"
import { adminApi } from "@/lib/api"
import type { AdminVectorStoreStats } from "@/types/api"
import { authClient } from "@/lib/auth-client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function dimensionBreakdown(stats: AdminVectorStoreStats): string {
    const entries = Object.entries(stats.stored_dimensions)
    if (!entries.length) return "No embeddings stored"
    return entries
        .map(([dim, count]) => `${dim}-d: ${count.toLocaleString()} chunk(s)`)
        .join(" · ")
}

export function VectorStoreSection() {
    const { data: session } = authClient.useSession()
    const isSuperadmin = (session?.user as { role?: string } | undefined)?.role === "superadmin"

    const [stats, setStats] = useState<AdminVectorStoreStats | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [busyAction, setBusyAction] = useState<"wipe" | "delete" | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)

    const load = useCallback(async (refreshOnly = false) => {
        if (refreshOnly) setIsRefreshing(true)
        else setIsLoading(true)
        setError(null)
        try {
            const data = await adminApi.getVectorStoreStats()
            setStats(data)
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to load vector store stats")
        } finally {
            setIsLoading(false)
            setIsRefreshing(false)
        }
    }, [])

    useEffect(() => {
        void load()
    }, [load])

    const runAction = async (action: "wipe" | "delete") => {
        const label =
            action === "wipe"
                ? "clear ALL embeddings (chunk text is kept; you must re-ingest)"
                : "delete ALL document chunks (text and vectors removed)"
        if (!window.confirm(`This will ${label}. Continue?`)) return

        setBusyAction(action)
        setError(null)
        setSuccess(null)
        try {
            const result =
                action === "wipe"
                    ? await adminApi.wipeVectorEmbeddings()
                    : await adminApi.deleteAllVectorChunks()
            setSuccess(result.message)
            await load(true)
        } catch (e) {
            setError(e instanceof Error ? e.message : "Action failed")
        } finally {
            setBusyAction(null)
        }
    }

    return (
        <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
                <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5" />
                        Vector store
                    </CardTitle>
                    <CardDescription>
                        pgvector embeddings used for semantic search. Query and ingest must use the
                        same dimension (Gemini via <code className="text-xs">GEMINI_EMBEDDING_DIMENSION</code>
                        ).
                    </CardDescription>
                </div>
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void load(true)}
                    disabled={isLoading || isRefreshing}
                >
                    {isRefreshing ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <RefreshCw className="h-4 w-4" />
                    )}
                    <span className="sr-only">Refresh</span>
                </Button>
            </CardHeader>
            <CardContent className="space-y-6">
                {isLoading && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading vector store…
                    </div>
                )}

                {error && (
                    <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="rounded-lg border border-green-500/40 bg-green-500/10 px-4 py-3 text-sm text-green-800 dark:text-green-200">
                        {success}
                    </div>
                )}

                {stats && !isLoading && (
                    <>
                        {stats.dimension_mismatch && (
                            <div className="flex gap-3 rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm">
                                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                                <div>
                                    <p className="font-medium text-amber-900 dark:text-amber-100">
                                        Dimension mismatch detected
                                    </p>
                                    <p className="mt-1 text-muted-foreground">
                                        Queries use {stats.configured_dimension}-d embeddings, but stored
                                        vectors or the DB column may differ. Clear embeddings and re-ingest
                                        all documents, or align{" "}
                                        <code className="text-xs">GEMINI_EMBEDDING_DIMENSION</code> with your
                                        data.
                                    </p>
                                </div>
                            </div>
                        )}

                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            <StatBlock
                                label="Configured dimension"
                                value={`${stats.configured_dimension}`}
                                hint={stats.embedding_model}
                            />
                            <StatBlock
                                label="DB column dimension"
                                value={
                                    stats.column_dimension != null
                                        ? String(stats.column_dimension)
                                        : "—"
                                }
                            />
                            <StatBlock
                                label="Approx. storage"
                                value={formatBytes(stats.storage_bytes)}
                                hint="sum of pg_column_size(embedding)"
                            />
                            <StatBlock
                                label="Chunks total"
                                value={stats.chunks_total.toLocaleString()}
                            />
                            <StatBlock
                                label="With embedding"
                                value={stats.chunks_with_embedding.toLocaleString()}
                            />
                            <StatBlock
                                label="Without embedding"
                                value={stats.chunks_without_embedding.toLocaleString()}
                            />
                        </div>

                        <div className="space-y-2">
                            <p className="text-sm font-medium">Stored vector dimensions</p>
                            <p className="text-sm text-muted-foreground">{dimensionBreakdown(stats)}</p>
                        </div>

                        <Separator />

                        <div className="space-y-4">
                            <p className="text-sm font-medium">Maintenance</p>
                            {!isSuperadmin && (
                                <p className="text-sm text-muted-foreground">
                                    Superadmin role required to wipe or delete vector data.
                                </p>
                            )}
                            <div className="flex flex-col gap-3 sm:flex-row">
                                <Button
                                    type="button"
                                    variant="outline"
                                    disabled={!isSuperadmin || busyAction != null}
                                    onClick={() => void runAction("wipe")}
                                >
                                    {busyAction === "wipe" ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="mr-2 h-4 w-4" />
                                    )}
                                    Wipe embeddings
                                </Button>
                                <Button
                                    type="button"
                                    variant="destructive"
                                    disabled={!isSuperadmin || busyAction != null}
                                    onClick={() => void runAction("delete")}
                                >
                                    {busyAction === "delete" ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="mr-2 h-4 w-4" />
                                    )}
                                    Delete all chunks
                                </Button>
                            </div>
                            <ul className="list-inside list-disc text-xs text-muted-foreground">
                                <li>
                                    <strong>Wipe embeddings</strong> — sets <code>embedding</code> to NULL;
                                    chunk text remains. Re-ingest documents to rebuild vectors.
                                </li>
                                <li>
                                    <strong>Delete all chunks</strong> — removes every row in{" "}
                                    <code>document_chunks</code>. Documents are kept; full re-ingest required.
                                </li>
                            </ul>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    )
}

function StatBlock({
    label,
    value,
    hint,
}: {
    label: string
    value: string
    hint?: string
}) {
    return (
        <div className="rounded-lg border p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {label}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
            {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
    )
}
