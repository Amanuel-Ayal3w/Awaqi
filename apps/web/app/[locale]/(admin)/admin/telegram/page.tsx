"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import { ColumnDef } from "@tanstack/react-table"
import {
    AlertTriangle,
    ExternalLink,
    Eye,
    Loader2,
    MoreHorizontal,
    Play,
    RefreshCw,
    RotateCcw,
    Save,
    Trash2,
} from "lucide-react"
import { adminApi } from "@/lib/api"
import { adminDocumentReviewPath } from "@/lib/admin-routes"
import type {
    AdminTelegramConfig,
    AdminTelegramMessageItem,
    AdminTelegramRunItem,
} from "@/types/api"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

const TYPE_FILTER_ALL = "__all__"
const INGEST_FILTER_ALL = "__all__"

export default function AdminTelegramPage() {
    const router = useRouter()
    const locale = useLocale()
    const [config, setConfig] = useState<AdminTelegramConfig | null>(null)
    const [messages, setMessages] = useState<AdminTelegramMessageItem[]>([])
    const [total, setTotal] = useState(0)
    const [runs, setRuns] = useState<AdminTelegramRunItem[]>([])
    const [channel, setChannel] = useState("morwestaa")
    const [scrapeSince, setScrapeSince] = useState("2026-04-01")
    const [maxMessages, setMaxMessages] = useState("200")
    const [schedulerEnabled, setSchedulerEnabled] = useState(false)
    const [cronHour, setCronHour] = useState("1")
    const [cronMinute, setCronMinute] = useState("0")
    const [filterType, setFilterType] = useState(TYPE_FILTER_ALL)
    const [filterIngest, setFilterIngest] = useState(INGEST_FILTER_ALL)
    const [search, setSearch] = useState("")
    const [tableSearch, setTableSearch] = useState("")
    const [isLoading, setIsLoading] = useState(true)
    const [isScraping, setIsScraping] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [isClearing, setIsClearing] = useState(false)
    const [busyRowId, setBusyRowId] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [lastStats, setLastStats] = useState<string | null>(null)

    const loadMessages = useCallback(async () => {
        const msgRes = await adminApi.listTelegramMessages({
            limit: 500,
            channel: channel.replace(/^@/, ""),
            message_type: filterType === TYPE_FILTER_ALL ? undefined : filterType,
            ingest_filter: filterIngest === INGEST_FILTER_ALL ? undefined : filterIngest,
            search: search.trim() || undefined,
        })
        setMessages(msgRes.messages)
        setTotal(msgRes.total)
    }, [channel, filterType, filterIngest, search])

    const loadAll = useCallback(async () => {
        setError(null)
        try {
            const [cfg, runRes] = await Promise.all([
                adminApi.getTelegramConfig(),
                adminApi.getTelegramRuns(15),
            ])
            setConfig(cfg)
            setChannel(cfg.channel_username)
            setScrapeSince(cfg.scrape_since.slice(0, 10))
            setMaxMessages(String(cfg.max_messages_per_run))
            setSchedulerEnabled(cfg.scheduler_enabled)
            setCronHour(String(cfg.cron_hour))
            setCronMinute(String(cfg.cron_minute))
            setRuns(runRes.runs)
            await loadMessages()
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load Telegram scraper")
        } finally {
            setIsLoading(false)
        }
    }, [loadMessages])

    useEffect(() => {
        void loadAll()
    }, [loadAll])

    useEffect(() => {
        if (!isLoading) void loadMessages()
    }, [filterType, filterIngest, search, loadMessages, isLoading])

    const handleSaveConfig = async () => {
        setIsSaving(true)
        setError(null)
        try {
            const cfg = await adminApi.patchTelegramConfig({
                channel_username: channel.replace(/^@/, ""),
                scrape_since: scrapeSince,
                max_messages_per_run: parseInt(maxMessages, 10) || 200,
                scheduler_enabled: schedulerEnabled,
                cron_hour: parseInt(cronHour, 10) || 0,
                cron_minute: parseInt(cronMinute, 10) || 0,
            })
            setConfig(cfg)
            setSchedulerEnabled(cfg.scheduler_enabled)
            setCronHour(String(cfg.cron_hour))
            setCronMinute(String(cfg.cron_minute))
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to save config")
        } finally {
            setIsSaving(false)
        }
    }

    const handleScrape = async () => {
        setIsScraping(true)
        setError(null)
        setLastStats(null)
        try {
            const result = await adminApi.triggerTelegramScrape()
            const s = result.stats
            setLastStats(
                `seen ${s.messages_seen}, +${s.documents_inserted} docs, ` +
                    `${s.text_posts} text, ${s.pdf_posts} pdf, ${s.pptx_posts} pptx, ` +
                    `${s.image_posts} images, ${s.errors} errors`
            )
            await loadMessages()
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Scrape failed")
        } finally {
            setIsScraping(false)
        }
    }

    const handleClearAll = async () => {
        const ok = window.confirm(
            "Remove all tracked Telegram posts and linked Telegram documents? " +
                "You will need to run scrape again to re-fetch them with the new logic."
        )
        if (!ok) return
        setIsClearing(true)
        setError(null)
        try {
            const res = await adminApi.clearTelegramMessages({
                channel: channel.replace(/^@/, ""),
                delete_documents: true,
            })
            setLastStats(`Cleared ${res.deleted} tracked rows`)
            await loadMessages()
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Clear failed")
        } finally {
            setIsClearing(false)
        }
    }

    const handleReingest = useCallback(
        async (row: AdminTelegramMessageItem, force = false) => {
            setBusyRowId(row.id)
            setError(null)
            try {
                await adminApi.reingestTelegramMessage(row.id, { force_index: force })
                await loadMessages()
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Re-ingest failed")
            } finally {
                setBusyRowId(null)
            }
        },
        [loadMessages]
    )

    const handleRemove = useCallback(
        async (row: AdminTelegramMessageItem) => {
            const ok = window.confirm(
                "Remove this tracked row" +
                    (row.document_id ? " and delete its linked document?" : "?")
            )
            if (!ok) return
            setBusyRowId(row.id)
            setError(null)
            try {
                await adminApi.deleteTelegramMessage(row.id, { delete_document: true })
                await loadMessages()
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Delete failed")
            } finally {
                setBusyRowId(null)
            }
        },
        [loadMessages]
    )

    const openReview = useCallback(
        (docId: string) => {
            router.push(adminDocumentReviewPath(locale, docId, "documents"))
        },
        [locale, router]
    )

    const messageColumns: ColumnDef<AdminTelegramMessageItem>[] = useMemo(
        () => [
            {
                accessorKey: "posted_at",
                header: "Posted",
                enableSorting: true,
                sortingFn: (a, b) =>
                    new Date(a.original.posted_at).getTime() -
                    new Date(b.original.posted_at).getTime(),
                cell: ({ row }) => (
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(row.getValue("posted_at") as string).toLocaleString()}
                    </span>
                ),
            },
            {
                accessorKey: "message_type",
                header: "Type",
                enableSorting: true,
                cell: ({ row }) => {
                    const t = row.getValue("message_type") as string
                    const part = row.original.content_part
                    const skip = row.original.skip_reason
                    return (
                        <div className="flex flex-col gap-0.5">
                            <Badge variant="outline" className="w-fit font-mono text-[10px] uppercase">
                                {t}
                            </Badge>
                            {part !== t ? (
                                <span className="text-[10px] text-muted-foreground">{part}</span>
                            ) : null}
                            {skip === "not_indexed" ? (
                                <span className="text-[10px] text-muted-foreground">not indexed</span>
                            ) : null}
                        </div>
                    )
                },
            },
            {
                accessorKey: "text_preview",
                header: "Preview",
                enableSorting: true,
                cell: ({ row }) => (
                    <span className="line-clamp-2 max-w-[300px] text-xs">
                        {row.original.text_preview || row.original.file_name || "—"}
                    </span>
                ),
            },
            {
                accessorKey: "document_status",
                header: "Ingest",
                enableSorting: true,
                sortingFn: (a, b) =>
                    (a.original.document_status ?? "").localeCompare(
                        b.original.document_status ?? ""
                    ),
                cell: ({ row }) => {
                    const st = (row.getValue("document_status") as string | null)?.toLowerCase()
                    if (!st) {
                        const skip = row.original.skip_reason
                        return (
                            <span className="text-xs text-muted-foreground">
                                {skip ?? "—"}
                            </span>
                        )
                    }
                    return (
                        <span
                            className={cn(
                                "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
                                st === "indexed" &&
                                    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                                st === "requires_manual_review" &&
                                    "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
                                st === "failed" &&
                                    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                            )}
                        >
                            {st.replace(/_/g, " ")}
                        </span>
                    )
                },
            },
            {
                id: "actions",
                header: "Actions",
                enableSorting: false,
                cell: ({ row }) => {
                    const item = row.original
                    const busy = busyRowId === item.id
                    return (
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="outline" size="sm" disabled={busy}>
                                    {busy ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <MoreHorizontal className="h-4 w-4" />
                                    )}
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                {item.telegram_url ? (
                                    <DropdownMenuItem asChild>
                                        <a
                                            href={item.telegram_url}
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            <ExternalLink className="mr-2 h-4 w-4" />
                                            Open in Telegram
                                        </a>
                                    </DropdownMenuItem>
                                ) : null}
                                {item.document_id ? (
                                    <>
                                        <DropdownMenuItem
                                            onClick={() => openReview(item.document_id!)}
                                        >
                                            <Eye className="mr-2 h-4 w-4" />
                                            Review document
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                            onClick={() => void handleReingest(item, false)}
                                        >
                                            <RotateCcw className="mr-2 h-4 w-4" />
                                            Re-ingest
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                            onClick={() => void handleReingest(item, true)}
                                        >
                                            <RotateCcw className="mr-2 h-4 w-4" />
                                            Force re-ingest
                                        </DropdownMenuItem>
                                    </>
                                ) : null}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    className="text-destructive focus:text-destructive"
                                    onClick={() => void handleRemove(item)}
                                >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Remove
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    )
                },
            },
        ],
        [busyRowId, openReview, handleReingest, handleRemove]
    )

    const credsOk = config?.api_configured && config?.session_configured

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Telegram mining</h1>
                    <p className="text-muted-foreground max-w-2xl">
                        Scrape <strong>@morwestaa</strong> for text, PDF, PPTX, and images. Before a
                        full re-scrape with new logic, use <strong>Clear tracked posts</strong> so
                        messages are not skipped as unchanged.
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 shrink-0"
                    onClick={() => void loadAll()}
                    disabled={isLoading}
                >
                    <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {config && (!config.api_configured || !config.session_configured) ? (
                <Card className="border-amber-500/40 bg-amber-500/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base text-amber-900 dark:text-amber-100">
                            <AlertTriangle className="h-4 w-4" />
                            Setup required
                        </CardTitle>
                        <CardDescription className="text-amber-900/80 dark:text-amber-100/80">
                            Configure <code className="text-xs">TELEGRAM_API_ID</code>,{" "}
                            <code className="text-xs">TELEGRAM_API_HASH</code>, and{" "}
                            <code className="text-xs">TELEGRAM_SESSION_STRING</code> (see README).
                        </CardDescription>
                    </CardHeader>
                </Card>
            ) : null}

            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {lastStats ? (
                <p className="text-sm text-muted-foreground">{lastStats}</p>
            ) : null}

            <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Scraper config</CardTitle>
                        <CardDescription>Only messages on or after scrape-since are processed.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label>Channel</Label>
                            <Input
                                value={channel}
                                onChange={(e) => setChannel(e.target.value)}
                                placeholder="morwestaa"
                            />
                        </div>
                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label>Scrape since</Label>
                                <Input
                                    type="date"
                                    value={scrapeSince}
                                    onChange={(e) => setScrapeSince(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Max messages / run</Label>
                                <Input
                                    value={maxMessages}
                                    onChange={(e) => setMaxMessages(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="rounded-md border p-3 space-y-3">
                            <div className="flex items-center justify-between gap-4">
                                <div>
                                    <Label htmlFor="tg-scheduler-enabled" className="text-sm font-medium">
                                        Daily scheduler
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        Auto-scrape on a cron schedule (Africa/Addis_Ababa)
                                    </p>
                                </div>
                                <Switch
                                    id="tg-scheduler-enabled"
                                    checked={schedulerEnabled}
                                    onCheckedChange={setSchedulerEnabled}
                                />
                            </div>
                            {schedulerEnabled && (
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                        <Label htmlFor="tg-cron-hour" className="text-xs">Hour (0–23)</Label>
                                        <Input
                                            id="tg-cron-hour"
                                            type="number"
                                            min={0}
                                            max={23}
                                            value={cronHour}
                                            onChange={(e) => setCronHour(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <Label htmlFor="tg-cron-minute" className="text-xs">Minute (0–59)</Label>
                                        <Input
                                            id="tg-cron-minute"
                                            type="number"
                                            min={0}
                                            max={59}
                                            value={cronMinute}
                                            onChange={(e) => setCronMinute(e.target.value)}
                                        />
                                    </div>
                                </div>
                            )}
                            {config?.next_run_time && (
                                <p className="text-xs text-muted-foreground">
                                    Next run:{" "}
                                    <span className="font-medium text-foreground">
                                        {new Date(config.next_run_time).toLocaleString()}
                                    </span>
                                </p>
                            )}
                        </div>

                        <div className="flex flex-wrap gap-2">
                            <Button
                                size="sm"
                                variant="secondary"
                                disabled={isSaving}
                                onClick={() => void handleSaveConfig()}
                            >
                                {isSaving ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Save className="mr-2 h-4 w-4" />
                                )}
                                Save config
                            </Button>
                            <Button
                                size="sm"
                                disabled={isScraping || !credsOk}
                                onClick={() => void handleScrape()}
                            >
                                {isScraping ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Play className="mr-2 h-4 w-4" />
                                )}
                                Run scrape
                            </Button>
                            <Button
                                size="sm"
                                variant="destructive"
                                disabled={isClearing}
                                onClick={() => void handleClearAll()}
                            >
                                {isClearing ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Trash2 className="mr-2 h-4 w-4" />
                                )}
                                Clear tracked posts
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Run history</CardTitle>
                        <CardDescription>{runs.length} recent runs</CardDescription>
                    </CardHeader>
                    <CardContent className="max-h-64 overflow-y-auto space-y-2 text-xs font-mono">
                        {runs.length === 0 ? (
                            <p className="text-muted-foreground">No runs yet.</p>
                        ) : (
                            runs.map((r) => (
                                <div key={r.id} className="rounded border px-2 py-1.5">
                                    <span className="text-muted-foreground">
                                        {new Date(r.started_at).toLocaleString()}
                                    </span>{" "}
                                    <Badge variant="outline" className="ml-1 text-[10px]">
                                        {r.status}
                                    </Badge>
                                    {r.stats ? (
                                        <p className="mt-1 text-muted-foreground">
                                            seen {r.stats.messages_seen} · docs +
                                            {r.stats.documents_inserted}
                                        </p>
                                    ) : null}
                                </div>
                            ))
                        )}
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Scraped messages</CardTitle>
                    <CardDescription>
                        {total} tracked rows (server) · click column headers to sort
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading…</p>
                    ) : (
                        <DataTable
                            columns={messageColumns}
                            data={messages}
                            initialPageSize={20}
                            pageSizeOptions={[20, 50, 100]}
                            globalFilter={tableSearch}
                            toolbar={
                                <>
                                    <div className="space-y-1">
                                        <Label className="text-xs">Search preview</Label>
                                        <Input
                                            className="h-8 w-[200px]"
                                            placeholder="Filter preview…"
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-xs">Table search</Label>
                                        <Input
                                            className="h-8 w-[160px]"
                                            placeholder="Quick filter…"
                                            value={tableSearch}
                                            onChange={(e) => setTableSearch(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-xs">Type</Label>
                                        <Select value={filterType} onValueChange={setFilterType}>
                                            <SelectTrigger className="h-8 w-[130px]">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value={TYPE_FILTER_ALL}>All</SelectItem>
                                                <SelectItem value="text">text</SelectItem>
                                                <SelectItem value="image">image</SelectItem>
                                                <SelectItem value="pdf">pdf</SelectItem>
                                                <SelectItem value="pptx">pptx</SelectItem>
                                                <SelectItem value="video">video</SelectItem>
                                                <SelectItem value="unsupported">unsupported</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-xs">Ingest</Label>
                                        <Select value={filterIngest} onValueChange={setFilterIngest}>
                                            <SelectTrigger className="h-8 w-[140px]">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value={INGEST_FILTER_ALL}>All</SelectItem>
                                                <SelectItem value="indexed">indexed</SelectItem>
                                                <SelectItem value="manual">needs review</SelectItem>
                                                <SelectItem value="failed">failed</SelectItem>
                                                <SelectItem value="none">not indexed</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </>
                            }
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
