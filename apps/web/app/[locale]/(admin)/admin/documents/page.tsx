"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import { ColumnDef } from "@tanstack/react-table"
import { Eye, Globe, RefreshCw, Search, Upload } from "lucide-react"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type { AdminDocumentItem, AdminUserItem } from "@/types/api"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { authClient } from "@/lib/auth-client"

type DocRow = AdminDocumentItem
type SourceFilter = "all" | "scraped" | "uploaded"

function StatusBadge({ status, stage }: { status: string; stage?: string | null }) {
    const s = status.toLowerCase()
    return (
        <div className="flex flex-col gap-0.5">
            <span
                className={cn(
                    "inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-semibold",
                    s === "indexed" &&
                        "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                    (s === "pending" || s === "processing") &&
                        "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
                    s === "failed" &&
                        "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                    s === "requires_manual_review" &&
                        "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
                )}
            >
                {s.replace(/_/g, " ")}
            </span>
            {stage ? <span className="text-[10px] text-muted-foreground">{stage}</span> : null}
        </div>
    )
}

export default function AdminDocumentsPage() {
    const router = useRouter()
    const locale = useLocale()
    const { data: session } = authClient.useSession()
    const role = (session?.user as any)?.role as string | undefined
    const isSuperadmin = role === "superadmin"

    const [allDocuments, setAllDocuments] = useState<DocRow[]>([])
    const [users, setUsers] = useState<AdminUserItem[]>([])
    const [filterUploaderId, setFilterUploaderId] = useState<string>("all")
    const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all")
    const [searchQuery, setSearchQuery] = useState("")
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [error, setError] = useState<string | null>(null)

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
            const opts: Parameters<typeof adminApi.listDocuments>[0] = { limit: 500 }
            if (isSuperadmin && filterUploaderId !== "all") {
                opts.uploaded_by = filterUploaderId
            }
            const result = await adminApi.listDocuments(opts)
            setAllDocuments(result.documents)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load documents")
        } finally {
            setIsLoading(false)
            setIsRefreshing(false)
        }
    }, [filterUploaderId, isSuperadmin])

    useEffect(() => { void loadUsers() }, [loadUsers])
    useEffect(() => { void refreshDocuments() }, [refreshDocuments])

    const openReview = useCallback(
        (docId: string) => router.push(adminDocumentReviewPath(locale, docId, "documents")),
        [locale, router]
    )

    const filteredDocuments = useMemo(() => {
        let docs = allDocuments
        if (sourceFilter === "scraped") docs = docs.filter((d) => !!d.source_url)
        if (sourceFilter === "uploaded") docs = docs.filter((d) => !d.source_url)
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase()
            docs = docs.filter(
                (d) =>
                    d.title.toLowerCase().includes(q) ||
                    (d.source_url ?? "").toLowerCase().includes(q) ||
                    (d.uploaded_by_email ?? "").toLowerCase().includes(q)
            )
        }
        return docs
    }, [allDocuments, sourceFilter, searchQuery])

    const scrapedCount = useMemo(() => allDocuments.filter((d) => !!d.source_url).length, [allDocuments])
    const uploadedCount = useMemo(() => allDocuments.filter((d) => !d.source_url).length, [allDocuments])

    const columns: ColumnDef<DocRow>[] = useMemo(
        () => [
            {
                accessorKey: "title",
                header: "Title",
                cell: ({ row }) => (
                    <div className="flex flex-col gap-0.5 max-w-[260px]">
                        <span className="font-medium line-clamp-2 leading-snug">
                            {row.getValue("title") as string}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                            {row.original.id.slice(0, 8)}…
                        </span>
                    </div>
                ),
            },
            {
                id: "source",
                header: "Source",
                cell: ({ row }) => {
                    const url = row.original.source_url
                    if (url) {
                        return (
                            <div className="flex flex-col gap-1 max-w-[220px]">
                                <Badge
                                    variant="outline"
                                    className="w-fit gap-1 border-blue-300 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-700"
                                >
                                    <Globe className="h-3 w-3" />
                                    Scraped
                                </Badge>
                                <a
                                    href={url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[10px] text-primary underline-offset-2 hover:underline break-all line-clamp-2"
                                >
                                    {url}
                                </a>
                            </div>
                        )
                    }
                    return (
                        <Badge
                            variant="outline"
                            className="gap-1 border-violet-300 bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-700"
                        >
                            <Upload className="h-3 w-3" />
                            Manual upload
                        </Badge>
                    )
                },
            },
            {
                accessorKey: "uploaded_by_email",
                header: "Uploaded by",
                cell: ({ row }) => {
                    const email = row.original.uploaded_by_email
                    const name = row.original.uploaded_by_name
                    if (!email && !name) return <span className="text-xs text-muted-foreground">—</span>
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
                cell: ({ row }) => (
                    <StatusBadge
                        status={row.getValue("status") as string}
                        stage={row.original.processing_stage}
                    />
                ),
            },
            {
                accessorKey: "byte_size",
                header: "Size",
                cell: ({ row }) => {
                    const n = row.getValue("byte_size") as number | null | undefined
                    if (n == null) return <span className="text-xs text-muted-foreground">—</span>
                    if (n < 1024) return <span className="text-xs">{n} B</span>
                    if (n < 1_048_576) return <span className="text-xs">{(n / 1024).toFixed(1)} KB</span>
                    return <span className="text-xs">{(n / 1_048_576).toFixed(1)} MB</span>
                },
            },
            {
                accessorKey: "created_at",
                header: "Added",
                cell: ({ row }) => (
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(row.getValue("created_at") as string).toLocaleString()}
                    </span>
                ),
            },
            {
                id: "actions",
                header: "",
                cell: ({ row }) => (
                    <Button
                        variant="outline"
                        size="sm"
                        className="gap-1"
                        onClick={() => openReview(row.original.id)}
                    >
                        <Eye className="h-3.5 w-3.5" />
                        View
                    </Button>
                ),
            },
        ],
        [openReview]
    )

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
                    <p className="text-muted-foreground">
                        All documents in the knowledge base — scraped from MoR and manually uploaded.
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

            {/* Summary chips */}
            {!isLoading && (
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => setSourceFilter("all")}
                        className={cn(
                            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                            sourceFilter === "all"
                                ? "border-foreground bg-foreground text-background"
                                : "border-border hover:bg-accent"
                        )}
                    >
                        All ({allDocuments.length})
                    </button>
                    <button
                        onClick={() => setSourceFilter("scraped")}
                        className={cn(
                            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                            sourceFilter === "scraped"
                                ? "border-blue-600 bg-blue-600 text-white"
                                : "border-blue-300 text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-700 dark:hover:bg-blue-950/40"
                        )}
                    >
                        <Globe className="mr-1 inline h-3 w-3" />
                        Scraped ({scrapedCount})
                    </button>
                    <button
                        onClick={() => setSourceFilter("uploaded")}
                        className={cn(
                            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                            sourceFilter === "uploaded"
                                ? "border-violet-600 bg-violet-600 text-white"
                                : "border-violet-300 text-violet-700 hover:bg-violet-50 dark:text-violet-400 dark:border-violet-700 dark:hover:bg-violet-950/40"
                        )}
                    >
                        <Upload className="mr-1 inline h-3 w-3" />
                        Uploaded ({uploadedCount})
                    </button>
                </div>
            )}

            {/* Filters row */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 min-w-[200px] max-w-sm">
                    <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Search by title, URL or uploader…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-8"
                    />
                </div>
                {isSuperadmin && (
                    <div className="flex items-center gap-2">
                        <Label className="text-sm font-medium whitespace-nowrap">Uploader</Label>
                        <Select value={filterUploaderId} onValueChange={setFilterUploaderId}>
                            <SelectTrigger className="w-[220px]">
                                <SelectValue placeholder="All uploaders" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All uploaders</SelectItem>
                                {users.map((u) => (
                                    <SelectItem key={u.id} value={u.id}>
                                        {u.email} {u.name ? `(${u.name})` : ""}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading documents…</p>
            ) : (
                <DataTable
                    columns={columns}
                    data={filteredDocuments}
                    initialPageSize={20}
                    pageSizeOptions={[20, 50, 100]}
                />
            )}
        </div>
    )
}
