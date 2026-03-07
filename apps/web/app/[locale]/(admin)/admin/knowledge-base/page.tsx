"use client"

import { useCallback, useEffect, useState } from "react"
import { DataTable } from "@/components/ui/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Upload, File, Loader2, Trash2, RefreshCw } from "lucide-react"
import { useDropzone } from "react-dropzone"
import { cn } from "@/lib/utils"
import { adminApi } from "@/lib/api"
import type { AdminDocumentItem, DocumentStatus } from "@/types/api"

type DocumentRow = {
    id: string
    title: string
    status: string
    source_url?: string | null
    created_at: string
}

const columns: ColumnDef<DocumentRow>[] = [
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
            return (
                <div
                    className={cn(
                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
                        status === "indexed" && "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                        status === "pending" && "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
                        status === "failed" && "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                    )}
                >
                    {status.toUpperCase()}
                </div>
            )
        },
    },
    {
        id: "actions",
        cell: () => (
            <div className="flex justify-end gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" disabled>
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>
        ),
    },
]

export default function KnowledgeBasePage() {
    const [uploadCount, setUploadCount] = useState(0)
    const [uploadError, setUploadError] = useState<string | null>(null)
    const [documents, setDocuments] = useState<DocumentRow[]>([])
    const [isRefreshing, setIsRefreshing] = useState(false)

    const isUploading = uploadCount > 0

    const mapDocument = (doc: AdminDocumentItem): DocumentRow => ({
        id: doc.id,
        title: doc.title,
        status: doc.status,
        source_url: doc.source_url ?? null,
        created_at: doc.created_at,
    })

    const refreshDocuments = useCallback(async () => {
        setIsRefreshing(true)
        setUploadError(null)
        try {
            const result = await adminApi.listDocuments(200)
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

    const handleUpload = async (file: File) => {
        setUploadCount((n) => n + 1)
        setUploadError(null)
        try {
            const result: DocumentStatus = await adminApi.uploadDocument(file)
            setDocuments((prev) => [
                {
                    id: result.doc_id,
                    title: file.name,
                    status: result.status,
                    source_url: null,
                    created_at: new Date().toISOString(),
                },
                ...prev,
            ])
            await refreshDocuments()
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Upload failed"
            setUploadError(message)
        } finally {
            setUploadCount((n) => n - 1)
        }
    }

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop: (acceptedFiles) => {
            acceptedFiles.forEach(handleUpload)
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
                    {uploadError && (
                        <p className="text-sm text-destructive mt-1">{uploadError}</p>
                    )}
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">Uploaded Documents</h2>
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
                <DataTable columns={columns} data={documents} />
            </div>
        </div>
    )
}
