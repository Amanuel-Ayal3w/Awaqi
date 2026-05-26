"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import { ColumnDef } from "@tanstack/react-table"
import { Eye, Loader2, Play, RefreshCw, Save } from "lucide-react"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type {
    AdminDocumentItem,
    AdminScrapeResult,
    AdminScraperConfig,
    AdminScraperRunItem,
    AdminScraperStatus,
} from "@/types/api"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"

type ScrapedDocumentRow = AdminDocumentItem

const STAT_KEYS = ["discovered", "inserted", "skipped", "errors"] as const

export default function AdminScraperPage() {
    const router = useRouter()
    const locale = useLocale()
    const [documents, setDocuments] = useState<ScrapedDocumentRow[]>([])
    const [scrapeResult, setScrapeResult] = useState<AdminScrapeResult | null>(null)
    const [scraperStatus, setScraperStatus] = useState<AdminScraperStatus | null>(null)
    const [runHistory, setRunHistory] = useState<AdminScraperRunItem[]>([])
    const [config, setConfig] = useState<AdminScraperConfig | null>(null)
    const [seedUrlsText, setSeedUrlsText] = useState("")
    const [cronHour, setCronHour] = useState("0")
    const [cronMinute, setCronMinute] = useState("0")
    const [maxLinks, setMaxLinks] = useState("30")
    const [schedulerEnabled, setSchedulerEnabled] = useState(true)
    const [shellLines, setShellLines] = useState<string[]>([
        "[ready] Scraper idle. Trigger a scrape to watch live updates.",
    ])
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [isScraping, setIsScraping] = useState(false)
    const [isSavingConfig, setIsSavingConfig] = useState(false)
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

    const applyConfigToForm = useCallback((c: AdminScraperConfig) => {
        setConfig(c)
        setSeedUrlsText(c.seed_urls.join("\n"))
        setCronHour(String(c.cron_hour))
        setCronMinute(String(c.cron_minute))
        setMaxLinks(String(c.max_links))
        setSchedulerEnabled(c.scheduler_enabled)
    }, [])

    const loadScraperMeta = useCallback(async () => {
        try {
            const [status, runs, cfg] = await Promise.all([
                adminApi.getScraperStatus(),
                adminApi.getScraperRuns(20),
                adminApi.getScraperConfig(),
            ])
            setScraperStatus(status)
            setRunHistory(runs.runs)
            applyConfigToForm(cfg)
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load scraper settings"
            setError(message)
        }
    }, [applyConfigToForm])

    const refreshDocuments = useCallback(async () => {
        setIsRefreshing(true)
        setError(null)
        try {
            const result = await adminApi.listDocuments({
                limit: 500,
                scraped_only: true,
            })
            setDocuments(result.documents)
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load scraped documents"
            setError(message)
        } finally {
            setIsLoading(false)
            setIsRefreshing(false)
        }
    }, [])

    useEffect(() => {
        void Promise.all([refreshDocuments(), loadScraperMeta()])
    }, [refreshDocuments, loadScraperMeta])

    const openReview = useCallback(
        (docId: string) => {
            router.push(adminDocumentReviewPath(locale, docId, "scraper"))
        },
        [locale, router]
    )

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
            STAT_KEYS.forEach((key) => {
                appendShellLine(`[stat] ${key}=${result.stats[key]}`)
            })
            await Promise.all([refreshDocuments(), loadScraperMeta()])
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to trigger scraper"
            setError(message)
            appendShellLine(`[error] ${message}`)
        } finally {
            clearInterval(liveTicker)
            setIsScraping(false)
        }
    }

    const handleSaveConfig = async () => {
        setIsSavingConfig(true)
        setError(null)
        try {
            const seeds = seedUrlsText
                .split(/[\n,]/)
                .map((s) => s.trim())
                .filter(Boolean)
            const updated = await adminApi.patchScraperConfig({
                seed_urls: seeds,
                scheduler_enabled: schedulerEnabled,
                cron_hour: Number.parseInt(cronHour, 10),
                cron_minute: Number.parseInt(cronMinute, 10),
                max_links: Number.parseInt(maxLinks, 10),
            })
            applyConfigToForm(updated)
            const status = await adminApi.getScraperStatus()
            setScraperStatus(status)
            appendShellLine("[ok] Scraper configuration saved.")
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to save configuration"
            setError(message)
        } finally {
            setIsSavingConfig(false)
        }
    }

    const columns: ColumnDef<ScrapedDocumentRow>[] = useMemo(
        () => [
            {
                accessorKey: "title",
                header: "Title",
                cell: ({ row }) => (
                    <span className="font-medium line-clamp-2 max-w-md">
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
                            className="text-xs text-primary underline-offset-4 hover:underline break-all line-clamp-2 max-w-xs"
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

    const runColumns: ColumnDef<AdminScraperRunItem>[] = useMemo(
        () => [
            {
                accessorKey: "started_at",
                header: "Started",
                cell: ({ row }) => (
                    <span className="text-xs whitespace-nowrap">
                        {new Date(row.getValue("started_at") as string).toLocaleString()}
                    </span>
                ),
            },
            { accessorKey: "trigger", header: "Trigger" },
            { accessorKey: "status", header: "Status" },
            {
                id: "inserted",
                header: "Inserted",
                cell: ({ row }) => row.original.stats?.inserted ?? "—",
            },
            {
                id: "discovered",
                header: "Discovered",
                cell: ({ row }) => row.original.stats?.discovered ?? "—",
            },
            {
                id: "skipped",
                header: "Skipped",
                cell: ({ row }) => row.original.stats?.skipped ?? "—",
            },
        ],
        []
    )

    const displayStats = scrapeResult?.stats ?? scraperStatus?.last_run?.stats

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Scraper</h1>
                <p className="text-muted-foreground">
                    Discover MoR law PDFs via the public API, store files on disk, and index into the
                    knowledge base.
                </p>
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Scheduler</CardTitle>
                        <CardDescription>
                            Daily scrape in {scraperStatus?.timezone ?? "Africa/Addis_Ababa"}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                        <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Enabled</span>
                            <span className="font-medium">
                                {scraperStatus?.scheduler_enabled ? "Yes" : "No"}
                            </span>
                        </div>
                        <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Cron time</span>
                            <span className="font-mono">
                                {String(scraperStatus?.cron_hour ?? 0).padStart(2, "0")}:
                                {String(scraperStatus?.cron_minute ?? 0).padStart(2, "0")}
                            </span>
                        </div>
                        <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Next run</span>
                            <span className="font-mono text-xs">
                                {scraperStatus?.next_run_time
                                    ? new Date(scraperStatus.next_run_time).toLocaleString()
                                    : "—"}
                            </span>
                        </div>
                        {config ? (
                            <div className="flex justify-between gap-4">
                                <span className="text-muted-foreground">Storage</span>
                                <span className="font-mono text-xs break-all">{config.storage_dir}</span>
                            </div>
                        ) : null}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Configuration</CardTitle>
                        <CardDescription>Seed listing pages and per-run limits</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between gap-4">
                            <Label htmlFor="scheduler-enabled">Daily scheduler</Label>
                            <Switch
                                id="scheduler-enabled"
                                checked={schedulerEnabled}
                                onCheckedChange={setSchedulerEnabled}
                            />
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label htmlFor="cron-hour">Hour</Label>
                                <Input
                                    id="cron-hour"
                                    type="number"
                                    min={0}
                                    max={23}
                                    value={cronHour}
                                    onChange={(e) => setCronHour(e.target.value)}
                                />
                            </div>
                            <div>
                                <Label htmlFor="cron-minute">Minute</Label>
                                <Input
                                    id="cron-minute"
                                    type="number"
                                    min={0}
                                    max={59}
                                    value={cronMinute}
                                    onChange={(e) => setCronMinute(e.target.value)}
                                />
                            </div>
                            <div>
                                <Label htmlFor="max-links">Max PDFs / run</Label>
                                <Input
                                    id="max-links"
                                    type="number"
                                    min={1}
                                    value={maxLinks}
                                    onChange={(e) => setMaxLinks(e.target.value)}
                                />
                            </div>
                        </div>
                        <div>
                            <Label htmlFor="seed-urls">Seed URLs (one per line)</Label>
                            <textarea
                                id="seed-urls"
                                className="mt-1 flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                                value={seedUrlsText}
                                onChange={(e) => setSeedUrlsText(e.target.value)}
                            />
                        </div>
                        <Button
                            className="gap-2"
                            onClick={() => void handleSaveConfig()}
                            disabled={isSavingConfig}
                        >
                            {isSavingConfig ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Save className="h-4 w-4" />
                            )}
                            Save configuration
                        </Button>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Scraper shell</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-emerald-300">
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
                        <div
                            ref={shellRef}
                            className="max-h-64 overflow-y-auto overscroll-contain"
                        >
                            <pre className="whitespace-pre-wrap break-words">{shellLines.join("\n")}</pre>
                            {isScraping ? (
                                <p className="mt-1 animate-pulse text-emerald-400">▋ running...</p>
                            ) : null}
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card>
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
                <CardContent>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading scraped documents…</p>
                    ) : (
                        <DataTable
                            columns={columns}
                            data={documents}
                            initialPageSize={10}
                            pageSizeOptions={[10, 50, 100]}
                        />
                    )}
                </CardContent>
            </Card>

            {displayStats ? (
                <Card>
                    <CardHeader>
                        <CardTitle>Latest scrape stats</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                        {STAT_KEYS.map((key) => (
                            <div key={key} className="rounded-md border p-3">
                                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                                    {key.replace(/_/g, " ")}
                                </p>
                                <p className="text-2xl font-semibold">{displayStats[key]}</p>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            ) : null}

            <Card>
                <CardHeader>
                    <CardTitle>Run history</CardTitle>
                    <CardDescription>Manual and scheduled scrape runs</CardDescription>
                </CardHeader>
                <CardContent>
                    <DataTable columns={runColumns} data={runHistory} initialPageSize={10} />
                </CardContent>
            </Card>

        </div>
    )
}
