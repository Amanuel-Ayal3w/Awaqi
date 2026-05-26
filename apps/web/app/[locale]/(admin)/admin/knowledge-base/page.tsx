"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { useLocale } from "next-intl"
import { DataTable } from "@/components/ui/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Upload, File, Loader2, Trash2, RefreshCw, FileSearch } from "lucide-react"
import { useDropzone } from "react-dropzone"
import { cn } from "@/lib/utils"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type { AdminDocumentItem, DocumentStatus } from "@/types/api"

type DocumentRow = {
    id: string
    title: string
    status: string
    source_url?: string | null
    created_at: string
    processing_stage?: string | null
    ingest_error?: string | null
}

function buildColumns(locale: string): ColumnDef<DocumentRow>[] {
    return [
        {
            accessorKey: "title",
            header: "Title",
            cell: ({ row }) => (
                <div className="flex items-center gap-2">
                    <File className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{row.getValue("title")}</span>
                </div>
            ),
        },
        {
            accessorKey: "id",
            header: "Document ID",
            cell: ({ row }) => (
                <span className="font-mono text-xs text-muted-foreground">
                    {(row.getValue("id") as string).slice(0, 8)}…
                </span>
            ),
        },
        {
            accessorKey: "source_url",
            header: "Source",
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground truncate block max-w-[280px]">
                    {(row.getValue("source_url") as string | null) ?? "manual upload"}
                </span>
            ),
        },
        {
            accessorKey: "created_at",
            header: "Created",
            cell: ({ row }) => {
                const value = row.getValue("created_at") as string
                return (
                    <span className="text-xs text-muted-foreground">
                        {new Date(value).toLocaleString()}
                    </span>
                )
            },
        },
        {
            accessorKey: "status",
            header: "Status",
            cell: ({ row }) => {
                const status = (row.getValue("status") as string).toLowerCase()
                const stage = row.original.processing_stage
                return (
                    <div className="flex flex-col gap-0.5">
                        <div
                            className={cn(
                                "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold w-fit",
                                status === "indexed" &&
                                    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                                (status === "pending" || status === "processing") &&
                                    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
                                status === "failed" &&
                                    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                                status === "requires_manual_review" &&
                                    "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
                            )}
                        >
                            {status.replace(/_/g, " ").toUpperCase()}
                        </div>
                        {stage ? (
                            <span className="text-[10px] text-muted-foreground">{stage}</span>
                        ) : null}
                    </div>
                )
            },
        },
        {
            id: "actions",
            cell: ({ row }) => {
                const isReview = row.original.status === "requires_manual_review"
                return (
                    <div className="flex justify-end gap-2">
                        {isReview && (
                            <Button asChild variant="outline" size="sm" className="gap-1.5 h-8">
                                <Link
                                    href={adminDocumentReviewPath(locale, row.original.id, "review-queue")}
                                >
                                    <FileSearch className="h-3.5 w-3.5" />
                                    Review
                                </Link>
                            </Button>
                        )}
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" disabled>
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                )
            },
        },
    ]
}

function parseDuplicateConflict(detail: unknown): string | null {
    if (
        detail !== null &&
        typeof detail === "object" &&
        !Array.isArray(detail) &&
        "code" in detail &&
        (detail as { code?: string }).code === "duplicate" &&
        "duplicate_of" in detail &&
        typeof (detail as { duplicate_of?: unknown }).duplicate_of === "string"
    ) {
        return (detail as { duplicate_of: string }).duplicate_of
    }
    return null
}

export default function KnowledgeBasePage() {
    const locale = useLocale()
    const columns = buildColumns(locale)
    const [uploadCount, setUploadCount] = useState(0)
    const [uploadError, setUploadError] = useState<string | null>(null)
    /** Same file hash as an existing document — user can overwrite via API. */
    const [duplicatePending, setDuplicatePending] = useState<{ file: File; duplicateOfId: string } | null>(
        null,
    )
    const [documents, setDocuments] = useState<DocumentRow[]>([])
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [scrapeBusy, setScrapeBusy] = useState(false)

    const isUploading = uploadCount > 0

    const mapDocument = (doc: AdminDocumentItem): DocumentRow => ({
        id: doc.id,
        title: doc.title,
        status: doc.status,
        source_url: doc.source_url ?? null,
        created_at: doc.created_at,
        processing_stage: doc.processing_stage ?? null,
        ingest_error: doc.ingest_error ?? null,
    })

    const refreshDocuments = useCallback(async () => {
        setIsRefreshing(true)
        try {
            const result = await adminApi.listDocuments({ limit: 200 })
            setDocuments(result.documents.map(mapDocument))
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load documents"
            setUploadError(message)
        } finally {
            setIsRefreshing(false)
        }
    }, [])

    useEffect(() => {
        void refreshDocuments()
    }, [refreshDocuments])

    useEffect(() => {
        const busy = documents.some(
            (d) =>
                d.status === "processing" ||
                d.status === "pending" ||
                !!d.processing_stage
        )
        if (!busy) return
        const t = setInterval(() => {
            void refreshDocuments()
        }, 2000)
        return () => clearInterval(t)
    }, [documents, refreshDocuments])

    const handleUpload = async (file: File, overwrite = false) => {
        setUploadCount((n) => n + 1)
        setUploadError(null)
        setDuplicatePending(null)
        try {
            const result: DocumentStatus = await adminApi.uploadDocument(file, { overwrite })
            setDocuments((prev) => [
                {
                    id: result.doc_id,
                    title: file.name,
                    status: result.status,
                    source_url: null,
                    created_at: new Date().toISOString(),
                    processing_stage: result.processing_stage ?? null,
                    ingest_error: result.ingest_error ?? null,
                },
                ...prev,
            ])
            await refreshDocuments()
        } catch (err: unknown) {
            if (
                typeof err === "object" &&
                err !== null &&
                "response" in err &&
                (err as { response?: { status?: number; data?: { detail?: unknown } } })
                    .response?.status === 409
            ) {
                const detail = (err as { response?: { data?: { detail?: unknown } } }).response
                    ?.data?.detail
                const dupId = parseDuplicateConflict(detail)
                if (dupId) {
                    setDuplicatePending({ file, duplicateOfId: dupId })
                } else {
                    const msg =
                        typeof detail === "string"
                            ? detail
                            : detail != null
                              ? JSON.stringify(detail)
                              : "Duplicate document"
                    setUploadError(`${msg}. Use overwrite if you meant to replace the existing file.`)
                }
            } else {
                const message = err instanceof Error ? err.message : "Upload failed"
                setUploadError(message)
            }
        } finally {
            setUploadCount((n) => n - 1)
        }
    }

    const handleScrape = async () => {
        setScrapeBusy(true)
        setUploadError(null)
        try {
            await adminApi.triggerScrape()
            await refreshDocuments()
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Scrape failed"
            setUploadError(message)
        } finally {
            setScrapeBusy(false)
        }
    }

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop: (acceptedFiles) => {
            acceptedFiles.forEach((file) => void handleUpload(file))
        },
        accept: {
            "application/pdf": [".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
            "text/plain": [".txt"],
        },
        multiple: true,
    })

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
                <p className="text-muted-foreground">
                    Manage the documents that power the AI&apos;s answers.
                </p>
            </div>

            <div
                {...getRootProps()}
                className={cn(
                    "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 text-center transition-colors hover:bg-muted/50 hover:cursor-pointer",
                    isDragActive ? "border-primary bg-muted" : "border-muted-foreground/25"
                )}
            >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center gap-2">
                    <div className="rounded-full bg-primary/10 p-4">
                        {isUploading ? (
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        ) : (
                            <Upload className="h-8 w-8 text-primary" />
                        )}
                    </div>
                    <h3 className="text-lg font-semibold">
                        {isUploading ? "Uploading…" : "Upload Documents"}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Drag and drop PDF, DOCX, or TXT files here, or click to select files.
                    </p>
                    {duplicatePending ? (
                        <div className="mt-2 flex max-w-md flex-col items-center gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-center">
                            <p className="text-sm text-foreground">
                                This file is identical to an existing document (
                                <span className="font-mono text-xs">{duplicatePending.duplicateOfId}</span>
                                ).
                            </p>
                            <div className="flex flex-wrap justify-center gap-2">
                                <Button
                                    size="sm"
                                    type="button"
                                    disabled={isUploading}
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        void handleUpload(duplicatePending.file, true)
                                    }}
                                >
                                    Overwrite existing
                                </Button>
                                <Button
                                    size="sm"
                                    type="button"
                                    variant="outline"
                                    disabled={isUploading}
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        setDuplicatePending(null)
                                    }}
                                >
                                    Cancel
                                </Button>
                            </div>
                        </div>
                    ) : uploadError ? (
                        <p className="text-sm text-destructive mt-1">{uploadError}</p>
                    ) : null}
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">Uploaded Documents</h2>
                    <div className="flex gap-2">
                        <Button
                            variant="secondary"
                            size="sm"
                            className="gap-2"
                            onClick={() => void handleScrape()}
                            disabled={scrapeBusy}
                        >
                            {scrapeBusy ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <RefreshCw className="h-4 w-4" />
                            )}
                            Sync / Scrape
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="gap-2"
                            onClick={() => void refreshDocuments()}
                            disabled={isRefreshing}
                        >
                            <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
                            Refresh
                        </Button>
                    </div>
                </div>
                <DataTable columns={columns} data={documents} />
            </div>
        </div>
    )
}
