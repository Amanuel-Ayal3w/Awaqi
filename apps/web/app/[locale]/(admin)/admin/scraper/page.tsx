"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ColumnDef } from "@tanstack/react-table"
import { Loader2, RefreshCw, Play } from "lucide-react"
import { adminApi } from "@/lib/api"
import type { AdminDocumentItem, AdminScrapeResult } from "@/types/api"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type ScrapedDocumentRow = AdminDocumentItem

export default function AdminScraperPage() {
    const [documents, setDocuments] = useState<ScrapedDocumentRow[]>([])
    const [scrapeResult, setScrapeResult] = useState<AdminScrapeResult | null>(null)
    const [shellLines, setShellLines] = useState<string[]>([
        "[ready] Scraper idle. Trigger a scrape to watch live updates.",
    ])
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [isScraping, setIsScraping] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const shellRef = useRef<HTMLDivElement | null>(null)

    const appendShellLine = useCallback((line: string) => {
        const timestamp = new Date().toLocaleTimeString()
        setShellLines((prev) => [...prev.slice(-149), `[${timestamp}] ${line}`])
    }, [])

    useEffect(() => {
        if (shellRef.current) {
            shellRef.current.scrollTop = shellRef.current.scrollHeight
        }
    }, [shellLines])

    const refreshDocuments = useCallback(async () => {
        setIsRefreshing(true)
        setError(null)
        try {
            const result = await adminApi.listDocuments({ limit: 500 })
            setDocuments(result.documents.filter((doc) => Boolean(doc.source_url)))
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load scraped documents"
            setError(message)
        } finally {
            setIsLoading(false)
            setIsRefreshing(false)
        }
    }, [])

    useEffect(() => {
        void refreshDocuments()
    }, [refreshDocuments])

    const handleTriggerScrape = async () => {
        setIsScraping(true)
        setError(null)
        appendShellLine("$ POST /v1/admin/scrape")
        appendShellLine("[info] Starting scrape cycle...")
        let heartbeat = 0
        const liveTicker = setInterval(() => {
            heartbeat = (heartbeat + 1) % 3
            appendShellLine(`[live] scraping${".".repeat(heartbeat + 1)}`)
        }, 1200)
        try {
            const result = await adminApi.triggerScrape()
            setScrapeResult(result)
            appendShellLine("[ok] Scrape completed.")
            Object.entries(result.stats).forEach(([key, value]) => {
                appendShellLine(`[stat] ${key}=${value}`)
            })
            await refreshDocuments()
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to trigger scraper"
            setError(message)
            appendShellLine(`[error] ${message}`)
        } finally {
            clearInterval(liveTicker)
            setIsScraping(false)
        }
    }

    const columns: ColumnDef<ScrapedDocumentRow>[] = useMemo(
        () => [
            {
                accessorKey: "title",
                header: "Title",
                cell: ({ row }) => (
                    <span className="font-medium line-clamp-2 max-w-[280px]">
                        {row.getValue("title") as string}
                    </span>
                ),
            },
            {
                accessorKey: "source_url",
                header: "Source URL",
                cell: ({ row }) => {
                    const sourceUrl = row.original.source_url
                    if (!sourceUrl) return <span className="text-xs text-muted-foreground">—</span>
                    return (
                        <a
                            href={sourceUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-primary underline-offset-4 hover:underline break-all"
                        >
                            {sourceUrl}
                        </a>
                    )
                },
            },
            {
                accessorKey: "status",
                header: "Status",
                cell: ({ row }) => {
                    const status = (row.getValue("status") as string).toLowerCase()
                    return (
                        <span
                            className={cn(
                                "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
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
                    )
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
        ],
        []
    )

    return (
        <div className="space-y-6">
            <div>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Scraper</h1>
                    <p className="text-muted-foreground">
                        Run the MoR scraper and review the documents discovered from web sources.
                    </p>
                </div>
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <div className="grid gap-6 lg:grid-cols-2">
                <Card className="flex h-full flex-col">
                    <CardHeader>
                        <CardTitle>Scraper shell</CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1">
                        <div className="flex h-full flex-col rounded-md border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-emerald-300">
                            <div className="mb-3 flex items-center justify-start">
                                <Button
                                    size="sm"
                                    className="gap-2"
                                    onClick={() => void handleTriggerScrape()}
                                    disabled={isScraping}
                                >
                                    {isScraping ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Play className="h-4 w-4" />
                                    )}
                                    Trigger scraper
                                </Button>
                            </div>
                            <div ref={shellRef} className="h-56 flex-1 overflow-auto">
                                <pre className="whitespace-pre-wrap break-words">{shellLines.join("\n")}</pre>
                                {isScraping ? <p className="mt-1 animate-pulse text-emerald-400">▋ running...</p> : null}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="flex h-full flex-col">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0">
                        <CardTitle>Scraped documents</CardTitle>
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
                    </CardHeader>
                    <CardContent className="flex-1 overflow-auto">
                        {isLoading ? (
                            <p className="text-sm text-muted-foreground">Loading scraped documents…</p>
                        ) : (
                            <DataTable columns={columns} data={documents} />
                        )}
                    </CardContent>
                </Card>
            </div>

            {scrapeResult ? (
                <Card>
                    <CardHeader>
                        <CardTitle>Latest scrape stats</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                        {Object.entries(scrapeResult.stats).length ? (
                            Object.entries(scrapeResult.stats).map(([key, value]) => (
                                <div key={key} className="rounded-md border p-3">
                                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                                        {key.replace(/_/g, " ")}
                                    </p>
                                    <p className="text-2xl font-semibold">{value}</p>
                                </div>
                            ))
                        ) : (
                            <p className="text-sm text-muted-foreground">No scrape stats returned.</p>
                        )}
                    </CardContent>
                </Card>
            ) : null}
        </div>
    )
}
