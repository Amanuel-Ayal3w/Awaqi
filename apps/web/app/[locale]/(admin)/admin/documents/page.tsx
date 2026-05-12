"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { ColumnDef } from "@tanstack/react-table"
import { Eye, Loader2, RefreshCw } from "lucide-react"
import { adminApi } from "@/lib/api"
import type { AdminDocumentDetail, AdminDocumentItem, AdminUserItem } from "@/types/api"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { authClient } from "@/lib/auth-client"

type DocRow = AdminDocumentItem

export default function AdminDocumentsPage() {
    const { data: session } = authClient.useSession()
    const role = (session?.user as any)?.role as string | undefined
    const isSuperadmin = role === "superadmin"

    const [documents, setDocuments] = useState<DocRow[]>([])
    const [users, setUsers] = useState<AdminUserItem[]>([])
    const [filterUploaderId, setFilterUploaderId] = useState<string>("all")
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [detailOpen, setDetailOpen] = useState(false)
    const [detail, setDetail] = useState<AdminDocumentDetail | null>(null)
    const [detailLoading, setDetailLoading] = useState(false)
    const [ingestText, setIngestText] = useState("")
    const [ingestBusy, setIngestBusy] = useState(false)
    const [ingestError, setIngestError] = useState<string | null>(null)
    const [reassignId, setReassignId] = useState("")
    const [reassignBusy, setReassignBusy] = useState(false)
    const [reassignError, setReassignError] = useState<string | null>(null)

    const loadUsers = useCallback(async () => {
        if (!isSuperadmin) return
        try {
            const res = await adminApi.listUsers()
            setUsers(res.users)
        } catch {
            /* non-fatal */
        }
    }, [isSuperadmin])

    const refreshDocuments = useCallback(async () => {
        setIsRefreshing(true)
        setError(null)
        try {
            const opts =
                isSuperadmin && filterUploaderId !== "all"
                    ? { limit: 500, uploaded_by: filterUploaderId }
                    : { limit: 500 }
            const result = await adminApi.listDocuments(opts)
            setDocuments(result.documents)
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load documents"
            setError(message)
        } finally {
            setIsLoading(false)
            setIsRefreshing(false)
        }
    }, [filterUploaderId, isSuperadmin])

    useEffect(() => {
        void loadUsers()
    }, [loadUsers])

    useEffect(() => {
        void refreshDocuments()
    }, [refreshDocuments])

    const openDetail = async (docId: string) => {
        setDetailOpen(true)
        setDetailLoading(true)
        setIngestText("")
        setIngestError(null)
        setReassignError(null)
        setReassignId("")
        try {
            const d = await adminApi.getDocument(docId)
            setDetail(d)
            setReassignId(d.uploaded_by_id ?? "")
        } catch {
            setDetail(null)
        } finally {
            setDetailLoading(false)
        }
    }

    const handleIngest = async () => {
        if (!detail) return
        setIngestBusy(true)
        setIngestError(null)
        try {
            await adminApi.ingestPlainText(detail.id, ingestText)
            const d = await adminApi.getDocument(detail.id)
            setDetail(d)
            await refreshDocuments()
        } catch (err: unknown) {
            const ax = err as { response?: { data?: { detail?: string } } }
            const d = ax.response?.data?.detail
            setIngestError(typeof d === "string" ? d : "Ingest failed")
        } finally {
            setIngestBusy(false)
        }
    }

    const handleReassign = async () => {
        if (!detail || !isSuperadmin) return
        setReassignBusy(true)
        setReassignError(null)
        try {
            const trimmed = reassignId.trim()
            const body =
                trimmed === "" ? { uploaded_by_id: null as string | null } : { uploaded_by_id: trimmed }
            const d = await adminApi.patchDocument(detail.id, body)
            setDetail(d)
            await refreshDocuments()
        } catch (err: unknown) {
            const ax = err as { response?: { data?: { detail?: string } } }
            const d = ax.response?.data?.detail
            setReassignError(typeof d === "string" ? d : "Update failed")
        } finally {
            setReassignBusy(false)
        }
    }

    const columns: ColumnDef<DocRow>[] = useMemo(
        () => [
            {
                accessorKey: "title",
                header: "Title",
                cell: ({ row }) => (
                    <span className="font-medium line-clamp-2 max-w-[240px]">
                        {row.getValue("title") as string}
                    </span>
                ),
            },
            {
                accessorKey: "uploaded_by_email",
                header: "Uploader",
                cell: ({ row }) => {
                    const email = row.original.uploaded_by_email
                    const name = row.original.uploaded_by_name
                    if (!email && !name) {
                        return <span className="text-xs text-muted-foreground">—</span>
                    }
                    return (
                        <div className="flex flex-col text-xs">
                            {name ? <span>{name}</span> : null}
                            <span className="text-muted-foreground">{email ?? ""}</span>
                        </div>
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
                            <span
                                className={cn(
                                    "inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-semibold",
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
                                {status.replace(/_/g, " ")}
                            </span>
                            {stage ? (
                                <span className="text-[10px] text-muted-foreground">{stage}</span>
                            ) : null}
                        </div>
                    )
                },
            },
            {
                accessorKey: "byte_size",
                header: "Size",
                cell: ({ row }) => {
                    const n = row.getValue("byte_size") as number | null | undefined
                    if (n == null) return <span className="text-xs text-muted-foreground">—</span>
                    if (n < 1024) return <span className="text-xs">{n} B</span>
                    if (n < 1024 * 1024) return <span className="text-xs">{(n / 1024).toFixed(1)} KB</span>
                    return <span className="text-xs">{(n / (1024 * 1024)).toFixed(1)} MB</span>
                },
            },
            {
                accessorKey: "created_at",
                header: "Created",
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
                    <Button variant="outline" size="sm" className="gap-1" onClick={() => void openDetail(row.original.id)}>
                        <Eye className="h-3.5 w-3.5" />
                        View
                    </Button>
                ),
            },
        ],
        []
    )

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
                    <p className="text-muted-foreground">
                        Inspect ingestion status, filter by uploader (superadmin), and re-index from plain text when a
                        document is stuck in manual review.
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 shrink-0"
                    onClick={() => void refreshDocuments()}
                    disabled={isRefreshing}
                >
                    <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {isSuperadmin ? (
                <div className="flex flex-wrap items-center gap-3 rounded-lg border p-4">
                    <Label className="text-sm font-medium">Filter by uploader</Label>
                    <Select value={filterUploaderId} onValueChange={setFilterUploaderId}>
                        <SelectTrigger className="w-[280px]">
                            <SelectValue placeholder="All uploaders" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All documents</SelectItem>
                            {users.map((u) => (
                                <SelectItem key={u.id} value={u.id}>
                                    {u.email} {u.name ? `(${u.name})` : ""}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            ) : null}

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading documents…</p>
            ) : (
                <DataTable columns={columns} data={documents} />
            )}

            <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
                <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Document detail</DialogTitle>
                    </DialogHeader>
                    {detailLoading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : detail ? (
                        <div className="grid gap-3 text-sm">
                            <div>
                                <span className="text-muted-foreground">Title</span>
                                <p className="font-medium">{detail.title}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <span className="text-muted-foreground">Status</span>
                                    <p>{detail.status}</p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">Stage</span>
                                    <p>{detail.processing_stage ?? "—"}</p>
                                </div>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Ingest error</span>
                                <p className="break-words text-xs">{detail.ingest_error ?? "—"}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                    <span className="text-muted-foreground">Bytes</span>
                                    <p>{detail.byte_size ?? "—"}</p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">Registry key</span>
                                    <p className="break-all">{detail.registry_key ?? "—"}</p>
                                </div>
                            </div>
                            <div>
                                <span className="text-muted-foreground">File hash</span>
                                <p className="break-all font-mono text-xs">{detail.file_hash ?? "—"}</p>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Uploader</span>
                                <p>
                                    {detail.uploaded_by_email ?? "—"}
                                    {detail.uploaded_by_id ? (
                                        <span className="ml-1 font-mono text-xs text-muted-foreground">
                                            ({detail.uploaded_by_id})
                                        </span>
                                    ) : null}
                                </p>
                            </div>

                            <div className="space-y-2 border-t pt-3">
                                <Label htmlFor="ingest-plain">Plain text re-index</Label>
                                <Textarea
                                    id="ingest-plain"
                                    rows={8}
                                    placeholder="Paste corrected UTF-8 text…"
                                    value={ingestText}
                                    onChange={(e) => setIngestText(e.target.value)}
                                    disabled={ingestBusy}
                                />
                                {ingestError ? <p className="text-xs text-destructive">{ingestError}</p> : null}
                                <Button size="sm" onClick={() => void handleIngest()} disabled={ingestBusy}>
                                    {ingestBusy ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Re-indexing…
                                        </>
                                    ) : (
                                        "Submit text & re-index"
                                    )}
                                </Button>
                            </div>

                            {isSuperadmin ? (
                                <div className="space-y-2 border-t pt-3">
                                    <Label htmlFor="reassign-uploader">Re-attribute uploader (ba_user UUID)</Label>
                                    <Input
                                        id="reassign-uploader"
                                        placeholder="UUID or empty for none"
                                        value={reassignId}
                                        onChange={(e) => setReassignId(e.target.value)}
                                        disabled={reassignBusy}
                                        className="font-mono text-xs"
                                    />
                                    {reassignError ? <p className="text-xs text-destructive">{reassignError}</p> : null}
                                    <Button size="sm" variant="secondary" onClick={() => void handleReassign()} disabled={reassignBusy}>
                                        {reassignBusy ? "Saving…" : "Save uploader"}
                                    </Button>
                                </div>
                            ) : null}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">Could not load document.</p>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDetailOpen(false)}>
                            Close
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
