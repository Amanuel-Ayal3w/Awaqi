"use client"

import { useCallback, useEffect, useState } from "react"
import { useLocale } from "next-intl"
import Link from "next/link"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { RefreshCw, ClipboardCheck, AlertTriangle, FileSearch } from "lucide-react"
import { cn } from "@/lib/utils"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type { AdminDocumentItem } from "@/types/api"

const REVIEW_REASON_LABELS: Record<string, string> = {
    low_ocr_confidence: "Low OCR confidence",
    poor_text_quality: "Poor text quality",
    corrupt_embedded_text: "Corrupt embedded text",
    amh_traineddata_missing: "Amharic OCR data missing",
    manual_review: "Manual review required",
}

function reviewReasonLabel(reason: string | null | undefined): string {
    if (!reason) return "Unknown"
    return REVIEW_REASON_LABELS[reason] ?? reason.replace(/_/g, " ")
}

type ReviewRow = AdminDocumentItem & { review_reason: string }

export default function ReviewQueuePage() {
    const locale = useLocale()
    const [rows, setRows] = useState<ReviewRow[]>([])
    const [total, setTotal] = useState(0)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const refresh = useCallback(async () => {
        setIsLoading(true)
        setError(null)
        try {
            const result = await adminApi.listDocuments({
                limit: 500,
                status: "requires_manual_review",
            })
            setRows(
                result.documents.map((d) => ({
                    ...d,
                    review_reason: d.ingest_error ?? "manual_review",
                }))
            )
            setTotal(result.total)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load review queue")
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        void refresh()
    }, [refresh])

    const columns: ColumnDef<ReviewRow>[] = [
        {
            accessorKey: "title",
            header: "Document",
            cell: ({ row }) => (
                <div className="flex flex-col gap-0.5">
                    <span className="font-medium leading-snug">{row.getValue("title")}</span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                        {row.original.id.slice(0, 8)}…
                    </span>
                </div>
            ),
        },
        {
            accessorKey: "review_reason",
            header: "Reason",
            cell: ({ row }) => {
                const reason = row.getValue("review_reason") as string
                return (
                    <Badge
                        variant="outline"
                        className="border-amber-400 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-700"
                    >
                        <AlertTriangle className="mr-1.5 h-3 w-3" />
                        {reviewReasonLabel(reason)}
                    </Badge>
                )
            },
        },
        {
            accessorKey: "source_url",
            header: "Source",
            cell: ({ row }) => {
                const url = row.getValue("source_url") as string | null
                return (
                    <span className="block max-w-[260px] truncate text-xs text-muted-foreground">
                        {url ?? "Manual upload"}
                    </span>
                )
            },
        },
        {
            accessorKey: "created_at",
            header: "Flagged",
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground">
                    {new Date(row.getValue("created_at") as string).toLocaleString()}
                </span>
            ),
        },
        {
            id: "actions",
            header: "",
            cell: ({ row }) => (
                <div className="flex justify-end">
                    <Button asChild size="sm" variant="outline" className="gap-1.5">
                        <Link
                            href={adminDocumentReviewPath(locale, row.original.id, "review-queue")}
                        >
                            <FileSearch className="h-3.5 w-3.5" />
                            Review
                        </Link>
                    </Button>
                </div>
            ),
        },
    ]

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                        <h1 className="text-3xl font-bold tracking-tight">Review Queue</h1>
                        {!isLoading && total > 0 && (
                            <Badge
                                variant="destructive"
                                className="rounded-full px-2 py-0.5 text-xs"
                            >
                                {total}
                            </Badge>
                        )}
                    </div>
                    <p className="text-muted-foreground">
                        Documents flagged during ingestion that need manual inspection before they
                        can be indexed.
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 shrink-0"
                    onClick={() => void refresh()}
                    disabled={isLoading}
                >
                    <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {error && (
                <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {error}
                </div>
            )}

            {!isLoading && rows.length === 0 && !error ? (
                <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-20 text-center">
                    <div className="rounded-full bg-green-100 p-4 dark:bg-green-900/30">
                        <ClipboardCheck className="h-8 w-8 text-green-600 dark:text-green-400" />
                    </div>
                    <h2 className="text-lg font-semibold">Queue is clear</h2>
                    <p className="max-w-sm text-sm text-muted-foreground">
                        No documents are waiting for manual review. New documents flagged by the
                        ingestion pipeline will appear here.
                    </p>
                </div>
            ) : (
                <DataTable columns={columns} data={rows} />
            )}
        </div>
    )
}
