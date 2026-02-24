"use client"

import { useState, useEffect } from "react"
import { DataTable } from "@/components/ui/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Upload, File, Loader2, Trash2, RefreshCw } from "lucide-react"
import { useDropzone } from "react-dropzone"
import { cn } from "@/lib/utils"
import { adminApi } from "@/lib/api"
import type { DocumentStatus } from "@/types/api"

type DocumentRow = {
    id: string
    title: string
    status: string
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
    const [isUploading, setIsUploading] = useState(false)
    const [uploadError, setUploadError] = useState<string | null>(null)
    const [documents, setDocuments] = useState<DocumentRow[]>([])

    const refreshDocuments = () => {
        // Documents list will be populated as uploads come in during this session.
        // A dedicated GET /v1/admin/documents endpoint can be added later for persistence.
    }

    useEffect(() => {
        refreshDocuments()
    }, [])

    const handleUpload = async (file: File) => {
        setIsUploading(true)
        setUploadError(null)
        try {
            const result: DocumentStatus = await adminApi.uploadDocument(file)
            setDocuments((prev) => [
                { id: result.doc_id, title: file.name, status: result.status },
                ...prev,
            ])
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Upload failed"
            setUploadError(message)
        } finally {
            setIsUploading(false)
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
                    <Button variant="outline" size="sm" className="gap-2" onClick={refreshDocuments}>
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </Button>
                </div>
                <DataTable columns={columns} data={documents} />
            </div>
        </div>
    )
}
