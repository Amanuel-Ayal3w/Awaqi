"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useLocale } from "next-intl"
import { DataTable } from "@/components/ui/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload, File, Loader2, Trash2, RefreshCw, FileSearch, Search, Filter, CheckCircle2, ShieldCheck, FileEdit } from "lucide-react"
import { JobProgress } from "@/components/ui/job-progress"
import { useDropzone } from "react-dropzone"
import { cn } from "@/lib/utils"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type { AdminDocumentItem, DocumentStatus, EnforcementStatus } from "@/types/api"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"

type StatusFilter = "all" | "indexed" | "pending" | "processing" | "failed" | "requires_manual_review"

const STATUS_LABELS: Record<StatusFilter, string> = {
    all: "All statuses",
    indexed: "Indexed",
    pending: "Pending",
    processing: "Processing",
    failed: "Failed",
    requires_manual_review: "Needs review",
}

type DocumentRow = {
    id: string
    title: string
    status: string
    enforcement_status: EnforcementStatus
    source_url?: string | null
    created_at: string
    processing_stage?: string | null
    ingest_error?: string | null
}

function EnforcementBadge({ value }: { value: EnforcementStatus }) {
    if (value === "in_effect") {
        return (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                <ShieldCheck className="h-3 w-3" />
                In Effect
            </span>
        )
    }
    return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            <FileEdit className="h-3 w-3" />
            Draft
        </span>
    )
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
            accessorKey: "enforcement_status",
            header: "Legal Status",
            cell: ({ row }) => (
                <EnforcementBadge value={row.getValue("enforcement_status") as EnforcementStatus} />
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
            header: "Index Status",
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
    const [searchQuery, setSearchQuery] = useState("")
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
    const [activeJobIds, setActiveJobIds] = useState<string[]>([])
    const [duplicatePending, setDuplicatePending] = useState<{
        file: File
        duplicateOfId: string
        enforcementStatus: EnforcementStatus
    } | null>(null)
    /** File(s) waiting for the user to pick a legal-status before uploading. */
    const [pendingFiles, setPendingFiles] = useState<File[]>([])
    const [selectedEnforcementStatus, setSelectedEnforcementStatus] =
        useState<EnforcementStatus>("in_effect")
    const [documents, setDocuments] = useState<DocumentRow[]>([])
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [scrapeBusy, setScrapeBusy] = useState(false)

    const isUploading = uploadCount > 0

    const filteredDocuments = useMemo(() => {
        let docs = documents
        if (statusFilter !== "all") docs = docs.filter((d) => d.status === statusFilter)
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase()
            docs = docs.filter((d) => d.title.toLowerCase().includes(q))
        }
        return docs
    }, [documents, statusFilter, searchQuery])

    const mapDocument = (doc: AdminDocumentItem): DocumentRow => ({
        id: doc.id,
        title: doc.title,
        status: doc.status,
        enforcement_status: doc.enforcement_status ?? "in_effect",
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

    const handleUpload = async (
        file: File,
        enforcementStatus: EnforcementStatus,
        overwrite = false,
    ) => {
        setUploadCount((n) => n + 1)
        setUploadError(null)
        setDuplicatePending(null)
        try {
            const result: DocumentStatus = await adminApi.uploadDocument(file, {
                overwrite,
                enforcement_status: enforcementStatus,
            })
            setDocuments((prev) => [
                {
                    id: result.doc_id,
                    title: file.name,
                    status: result.status,
                    enforcement_status: enforcementStatus,
                    source_url: null,
                    created_at: new Date().toISOString(),
                    processing_stage: result.processing_stage ?? null,
                    ingest_error: result.ingest_error ?? null,
                },
                ...prev,
            ])
            if (result.job_id) {
                setActiveJobIds((prev) => [...prev, result.job_id!])
            }
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
                    setDuplicatePending({ file, duplicateOfId: dupId, enforcementStatus })
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

    /** Called when the user confirms the legal status and clicks "Upload". */
    const confirmUpload = () => {
        const files = pendingFiles
        setPendingFiles([])
        files.forEach((file) => void handleUpload(file, selectedEnforcementStatus))
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
            if (acceptedFiles.length === 0) return
            setSelectedEnforcementStatus("in_effect")
            setPendingFiles(acceptedFiles)
            setUploadError(null)
            setDuplicatePending(null)
        },
        accept: {
            "application/pdf": [".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
            "text/plain": [".txt"],
        },
        multiple: true,
        noClick: pendingFiles.length > 0,
        noDrag: pendingFiles.length > 0,
    })

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
                <p className="text-muted-foreground">
                    Manage the documents that power the AI&apos;s answers.
                </p>
            </div>

            {/* ── Upload dropzone ───────────────────────────────────────────── */}
            <div
                {...getRootProps()}
                className={cn(
                    "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors hover:bg-muted/50 hover:cursor-pointer",
                    isDragActive ? "border-primary bg-muted" : "border-muted-foreground/25",
                    pendingFiles.length > 0 && "cursor-default hover:bg-transparent",
                )}
            >
                <input {...getInputProps()} />

                {/* ── Step 1: idle / dragging state ── */}
                {pendingFiles.length === 0 && !duplicatePending && (
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
                            Drag and drop PDF, DOCX, or TXT files here, or click to select.
                        </p>
                        {uploadError && (
                            <p className="text-sm text-destructive mt-1">{uploadError}</p>
                        )}
                    </div>
                )}

                {/* ── Step 2: legal-status picker ── */}
                {pendingFiles.length > 0 && (
                    <div
                        className="flex w-full max-w-md flex-col gap-4"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex flex-col items-center gap-1">
                            <File className="h-8 w-8 text-primary" />
                            <p className="text-sm font-medium">
                                {pendingFiles.length === 1
                                    ? pendingFiles[0].name
                                    : `${pendingFiles.length} files selected`}
                            </p>
                        </div>

                        <div className="rounded-lg border bg-card p-4 text-left shadow-sm">
                            <p className="mb-3 text-sm font-semibold">
                                What is the legal status of{" "}
                                {pendingFiles.length === 1 ? "this document" : "these documents"}?
                            </p>

                            <div className="flex flex-col gap-2">
                                <label
                                    className={cn(
                                        "flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors",
                                        selectedEnforcementStatus === "in_effect"
                                            ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                                            : "hover:bg-muted/50",
                                    )}
                                >
                                    <input
                                        type="radio"
                                        name="enforcement_status"
                                        value="in_effect"
                                        checked={selectedEnforcementStatus === "in_effect"}
                                        onChange={() => setSelectedEnforcementStatus("in_effect")}
                                        className="mt-0.5"
                                    />
                                    <div>
                                        <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                                            Currently in Effect
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            This regulation or proclamation is active and binding law.
                                        </p>
                                    </div>
                                </label>

                                <label
                                    className={cn(
                                        "flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors",
                                        selectedEnforcementStatus === "draft"
                                            ? "border-amber-500 bg-amber-50 dark:bg-amber-900/20"
                                            : "hover:bg-muted/50",
                                    )}
                                >
                                    <input
                                        type="radio"
                                        name="enforcement_status"
                                        value="draft"
                                        checked={selectedEnforcementStatus === "draft"}
                                        onChange={() => setSelectedEnforcementStatus("draft")}
                                        className="mt-0.5"
                                    />
                                    <div>
                                        <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                                            Draft — Not Yet in Effect
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            Proposed or forthcoming rule; not yet legally binding.
                                        </p>
                                    </div>
                                </label>
                            </div>
                        </div>

                        <div className="flex justify-center gap-2">
                            <Button
                                size="sm"
                                onClick={confirmUpload}
                                disabled={isUploading}
                                className="gap-2"
                            >
                                {isUploading ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Upload className="h-4 w-4" />
                                )}
                                Upload
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                disabled={isUploading}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    setPendingFiles([])
                                    setUploadError(null)
                                }}
                            >
                                Cancel
                            </Button>
                        </div>
                        {uploadError && (
                            <p className="text-sm text-destructive text-center">{uploadError}</p>
                        )}
                    </div>
                )}

                {/* ── Duplicate resolution ── */}
                {duplicatePending && (
                    <div
                        className="mt-2 flex max-w-md flex-col items-center gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-center"
                        onClick={(e) => e.stopPropagation()}
                    >
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
                                onClick={() =>
                                    void handleUpload(
                                        duplicatePending.file,
                                        duplicatePending.enforcementStatus,
                                        true,
                                    )
                                }
                            >
                                Overwrite existing
                            </Button>
                            <Button
                                size="sm"
                                type="button"
                                variant="outline"
                                disabled={isUploading}
                                onClick={() => setDuplicatePending(null)}
                            >
                                Cancel
                            </Button>
                        </div>
                    </div>
                )}
            </div>

            {/* ── Active upload progress bars ───────────────────────────────── */}
            {activeJobIds.length > 0 && (
                <div className="space-y-2">
                    {activeJobIds.map((jobId) => (
                        <div key={jobId} className="rounded-lg border bg-card p-3">
                            <JobProgress
                                jobId={jobId}
                                label="Ingesting document…"
                                onDone={() => {
                                    setActiveJobIds((prev) => prev.filter((id) => id !== jobId))
                                    void refreshDocuments()
                                }}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* ── Document list ─────────────────────────────────────────────── */}
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
                <div className="flex flex-wrap items-center gap-3">
                    <div className="relative flex-1 min-w-[200px] max-w-sm">
                        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Search by title…"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-8"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Filter className="h-4 w-4 text-muted-foreground" />
                        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
                            <SelectTrigger className="w-[170px]">
                                <SelectValue placeholder="All statuses" />
                            </SelectTrigger>
                            <SelectContent>
                                {(Object.keys(STATUS_LABELS) as StatusFilter[]).map((s) => (
                                    <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
                <DataTable columns={columns} data={filteredDocuments} />
            </div>
        </div>
    )
}
