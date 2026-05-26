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
    Play,
    RefreshCw,
    Save,
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
import { cn } from "@/lib/utils"

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
    const [isLoading, setIsLoading] = useState(true)
    const [isScraping, setIsScraping] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [lastStats, setLastStats] = useState<string | null>(null)

    const loadAll = useCallback(async () => {
        setError(null)
        try {
            const [cfg, msgRes, runRes] = await Promise.all([
                adminApi.getTelegramConfig(),
                adminApi.listTelegramMessages({ limit: 100 }),
                adminApi.getTelegramRuns(15),
            ])
            setConfig(cfg)
            setChannel(cfg.channel_username)
            setScrapeSince(cfg.scrape_since.slice(0, 10))
            setMaxMessages(String(cfg.max_messages_per_run))
            setMessages(msgRes.messages)
            setTotal(msgRes.total)
            setRuns(runRes.runs)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load Telegram scraper")
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        void loadAll()
    }, [loadAll])

    const handleSaveConfig = async () => {
        setIsSaving(true)
        setError(null)
        try {
            const cfg = await adminApi.patchTelegramConfig({
                channel_username: channel.replace(/^@/, ""),
                scrape_since: scrapeSince,
                max_messages_per_run: parseInt(maxMessages, 10) || 200,
            })
            setConfig(cfg)
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
                    `${s.pdf_posts} pdf, ${s.pptx_posts} pptx, ${s.text_posts} text, ` +
                    `${s.errors} errors`
            )
            await loadAll()
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Scrape failed")
        } finally {
            setIsScraping(false)
        }
    }

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
                cell: ({ row }) => (
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(row.getValue("posted_at") as string).toLocaleString()}
                    </span>
                ),
            },
            {
                accessorKey: "message_type",
                header: "Type",
                cell: ({ row }) => (
                    <Badge variant="outline" className="font-mono text-[10px] uppercase">
                        {row.getValue("message_type") as string}
                    </Badge>
                ),
            },
            {
                accessorKey: "text_preview",
                header: "Preview",
                cell: ({ row }) => (
                    <span className="line-clamp-2 max-w-[280px] text-xs">
                        {row.original.text_preview || row.original.file_name || "—"}
                    </span>
                ),
            },
            {
                accessorKey: "document_status",
                header: "Ingest",
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
                header: "",
                cell: ({ row }) => (
                    <div className="flex gap-1">
                        {row.original.telegram_url ? (
                            <Button variant="ghost" size="sm" asChild>
                                <a
                                    href={row.original.telegram_url!}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    <ExternalLink className="h-3.5 w-3.5" />
                                </a>
                            </Button>
                        ) : null}
                        {row.original.document_id ? (
                            <Button
                                variant="outline"
                                size="sm"
                                className="gap-1"
                                onClick={() => openReview(row.original.document_id!)}
                            >
                                <Eye className="h-3.5 w-3.5" />
                                Review
                            </Button>
                        ) : null}
                    </div>
                ),
            },
        ],
        [openReview]
    )

    const credsOk = config?.api_configured && config?.session_configured

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Telegram mining</h1>
                    <p className="text-muted-foreground max-w-2xl">
                        Scrape <strong>@morwestaa</strong> (text, PDF, PPTX) via Telethon. Uses MTProto —
                        not the Bot API — so channel history back to the configured date can be ingested
                        into the knowledge base.
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
                            Add <code className="text-xs">TELEGRAM_API_ID</code>,{" "}
                            <code className="text-xs">TELEGRAM_API_HASH</code> (from{" "}
                            <a
                                href="https://my.telegram.org/apps"
                                className="underline"
                                target="_blank"
                                rel="noreferrer"
                            >
                                my.telegram.org
                            </a>
                            ) and <code className="text-xs">TELEGRAM_SESSION_STRING</code> from{" "}
                            <code className="text-xs">uv run python scripts/telegram_gen_session.py</code>
                            . The Telegram account must be able to read @morwestaa.
                        </CardDescription>
                    </CardHeader>
                </Card>
            ) : null}

            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {lastStats ? (
                <p className="text-sm text-muted-foreground">Last run: {lastStats}</p>
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
                                    {r.error_message ? (
                                        <p className="mt-1 text-destructive">{r.error_message}</p>
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
                        {total} tracked posts ·{" "}
                        <Link href={`/${locale}/admin/documents`} className="text-primary underline">
                            all documents
                        </Link>
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
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
