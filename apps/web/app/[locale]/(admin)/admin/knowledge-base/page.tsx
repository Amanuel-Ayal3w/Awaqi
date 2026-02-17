"use client"

import { useState } from "react"
import { DataTable } from "@/components/ui/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload, File, Loader2, Trash2, RefreshCw } from "lucide-react"
import { useDropzone } from "react-dropzone"
import { cn } from "@/lib/utils"

// Type definition matching the SRS/SDS Document class
type Document = {
    id: string
    title: string
    fileType: "PDF" | "DOCX" | "TXT"
    uploadDate: string
    status: "PENDING" | "PROCESSING" | "INDEXED" | "FAILED"
    size: string
}

const data: Document[] = [
    {
        id: "1",
        title: "Proclamation No. 1234/2021",
        fileType: "PDF",
        uploadDate: "2023-10-24",
        status: "INDEXED",
        size: "2.4 MB",
    },
    {
        id: "2",
        title: "Labor Law Amendment 2023",
        fileType: "DOCX",
        uploadDate: "2023-10-25",
        status: "PROCESSING",
        size: "1.1 MB",
    },
    {
        id: "3",
        title: "Tax Regulation Guide",
        fileType: "PDF",
        uploadDate: "2023-10-26",
        status: "FAILED",
        size: "5.6 MB",
    },
]

const columns: ColumnDef<Document>[] = [
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
        accessorKey: "fileType",
        header: "Type",
    },
    {
        accessorKey: "size",
        header: "Size",
    },
    {
        accessorKey: "uploadDate",
        header: "Uploaded",
    },
    {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
            const status = row.getValue("status") as string
            return (
                <div
                    className={cn(
                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                        status === "INDEXED" && "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                        status === "PROCESSING" && "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
                        status === "FAILED" && "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                        status === "PENDING" && "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400",
                    )}
                >
                    {status}
                </div>
            )
        },
    },
    {
        id: "actions",
        cell: ({ row }) => {
            return (
                <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            )
        },
    },
]

export default function KnowledgeBasePage() {
    const [isUploading, setIsUploading] = useState(false)

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop: (acceptedFiles) => {
            setIsUploading(true)
            // TODO: Implement actual upload logic to FastAPI
            console.log("Uploading files:", acceptedFiles)
            setTimeout(() => setIsUploading(false), 2000)
        },
        accept: {
            'application/pdf': ['.pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'text/plain': ['.txt']
        }
    })

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
                <p className="text-muted-foreground">
                    Manage the documents that power the AI's answers.
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
                        {isUploading ? "Uploading..." : "Upload Documents"}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Drag and drop PDF, DOCX, or TXT files here, or click to select which documents to add to the knowledge base.
                    </p>
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">Indexed Documents</h2>
                    <Button variant="outline" size="sm" className="gap-2">
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </Button>
                </div>
                <DataTable columns={columns} data={data} />
            </div>
        </div>
    )
}
