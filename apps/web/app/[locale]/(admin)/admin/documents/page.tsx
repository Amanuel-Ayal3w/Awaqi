"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import { ColumnDef } from "@tanstack/react-table"
import { Eye, Loader2, RefreshCw } from "lucide-react"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type { AdminDocumentItem, AdminUserItem } from "@/types/api"
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
import { Label } from "@/components/ui/label"
import { authClient } from "@/lib/auth-client"

type DocRow = AdminDocumentItem

export default function AdminDocumentsPage() {
    const router = useRouter()
    const locale = useLocale()
    const { data: session } = authClient.useSession()
    const role = (session?.user as any)?.role as string | undefined
    const isSuperadmin = role === "superadmin"

    const [documents, setDocuments] = useState<DocRow[]>([])
    const [users, setUsers] = useState<AdminUserItem[]>([])
    const [filterUploaderId, setFilterUploaderId] = useState<string>("all")
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

    const openReview = useCallback(
        (docId: string) => {
            router.push(adminDocumentReviewPath(locale, docId, "documents"))
        },
        [locale, router]
    )

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
                    <Button variant="outline" size="sm" className="gap-1" onClick={() => openReview(row.original.id)}>
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
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
                    <p className="text-muted-foreground">
                        Open a document to review PDF and transcript side by side, correct OCR, and index. Superadmins
                        can filter by uploader.
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
                <DataTable
                    columns={columns}
                    data={documents}
                    initialPageSize={10}
                    pageSizeOptions={[10, 50, 100]}
                />
            )}

        </div>
    )
}
