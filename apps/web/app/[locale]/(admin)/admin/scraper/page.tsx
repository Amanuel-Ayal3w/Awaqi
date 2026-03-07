"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2, Play, Terminal } from "lucide-react"
import { cn } from "@/lib/utils"
import { adminApi } from "@/lib/api"
import type { ScraperJobStatus, ScraperStatus } from "@/types/api"

type LogEntry = {
    timestamp: string
    level: "INFO" | "WARN" | "ERROR"
    message: string
}

const INITIAL_LOGS: LogEntry[] = [
    { timestamp: new Date().toLocaleTimeString(), level: "INFO", message: "Scraper ready." },
]

export default function ScraperControlPage() {
    const [status, setStatus] = useState<"IDLE" | "RUNNING" | "COMPLETED" | "FAILED">("IDLE")
    const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS)
    const [duration, setDuration] = useState(0)
    const [currentJobId, setCurrentJobId] = useState<string | null>(null)
    const [jobStatus, setJobStatus] = useState<ScraperJobStatus | null>(null)
    const [triggerError, setTriggerError] = useState<string | null>(null)
    const scrollRef = useRef<HTMLDivElement>(null)
    const lastRemoteStatusRef = useRef<string | null>(null)

    useEffect(() => {
        let interval: NodeJS.Timeout
        if (status === "RUNNING") {
            interval = setInterval(() => setDuration((prev) => prev + 1), 1000)
        }
        return () => clearInterval(interval)
    }, [status])

    useEffect(() => {
        const viewport = scrollRef.current?.querySelector("[data-radix-scroll-area-viewport]")
        if (viewport) viewport.scrollTop = viewport.scrollHeight
    }, [logs])

    const appendLog = (level: LogEntry["level"], message: string) => {
        setLogs((prev) => [
            ...prev,
            { timestamp: new Date().toLocaleTimeString(), level, message },
        ])
    }

    useEffect(() => {
        if (!currentJobId || status !== "RUNNING") {
            return
        }

        let cancelled = false

        const poll = async () => {
            try {
                const result = await adminApi.getScraperStatus(currentJobId)
                if (cancelled) return

                setJobStatus(result)

                if (lastRemoteStatusRef.current !== result.status) {
                    lastRemoteStatusRef.current = result.status
                    appendLog("INFO", `Job status: ${result.status}`)
                }

                if (result.status === "completed") {
                    setStatus("COMPLETED")
                    setDuration(0)
                    appendLog(
                        "INFO",
                        `Completed. Found ${result.documents_found}, new ${result.documents_new}.`
                    )
                } else if (result.status === "failed") {
                    setStatus("FAILED")
                    setDuration(0)
                    appendLog("ERROR", `Failed: ${result.error ?? "unknown error"}`)
                } else if (result.status === "already_running") {
                    setStatus("IDLE")
                    setDuration(0)
                    appendLog("WARN", "Another scraper run is already active.")
                }
            } catch (err: unknown) {
                if (cancelled) return
                const maybeHttpErr = err as { response?: { status?: number } }
                if (maybeHttpErr.response?.status === 404) {
                    // Scraper may still be queued before first status is written.
                    return
                }
                const message = err instanceof Error ? err.message : "Unable to fetch scrape status"
                appendLog("WARN", message)
            }
        }

        void poll()
        const interval = setInterval(() => void poll(), 3000)

        return () => {
            cancelled = true
            clearInterval(interval)
        }
    }, [currentJobId, status])

    const handleStart = async () => {
        setTriggerError(null)
        try {
            const result: ScraperStatus = await adminApi.triggerScraper()
            setDuration(0)
            setJobStatus(null)
            lastRemoteStatusRef.current = null

            if (result.status === "already_running") {
                setCurrentJobId(null)
                setStatus("IDLE")
                appendLog("WARN", "Scraper is already running in another worker.")
                return
            }

            setCurrentJobId(result.job_id)
            setStatus("RUNNING")
            appendLog("INFO", `Scraper job queued — job_id: ${result.job_id}`)
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to start scraper"
            setTriggerError(msg)
            appendLog("ERROR", msg)
        }
    }

    const humanStatus =
        status === "RUNNING" ? "Running"
            : status === "COMPLETED" ? "Completed"
                : status === "FAILED" ? "Failed"
                    : "Idle"

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Scraper Control</h1>
                <p className="text-muted-foreground">
                    Monitor and control the web scraping service.
                </p>
            </div>

            {triggerError && (
                <p className="text-sm text-destructive">{triggerError}</p>
            )}

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Status</CardTitle>
                        <CardDescription>Current state of the scraper service</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div className="flex items-center gap-4">
                                <div className={cn("relative flex h-3 w-3", status === "RUNNING" && "animate-pulse")}>
                                    <span className={cn(
                                        "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                                        status === "RUNNING" ? "bg-green-400" : "hidden"
                                    )} />
                                    <span className={cn(
                                        "relative inline-flex rounded-full h-3 w-3",
                                        status === "RUNNING" ? "bg-green-500"
                                            : status === "COMPLETED" ? "bg-blue-500"
                                                : status === "FAILED" ? "bg-red-500"
                                                    : "bg-gray-400"
                                    )} />
                                </div>
                                <div className="space-y-1">
                                    <p className="font-medium leading-none">
                                        {humanStatus}
                                    </p>
                                    {status === "RUNNING" && (
                                        <p className="text-sm text-muted-foreground">Duration: {duration}s</p>
                                    )}
                                    {currentJobId && (
                                        <p className="text-xs font-mono text-muted-foreground">
                                            job: {currentJobId.slice(0, 8)}…
                                        </p>
                                    )}
                                </div>
                            </div>
                            <div className="flex gap-2">
                                <Button
                                    onClick={handleStart}
                                    className="gap-2"
                                    disabled={status === "RUNNING"}
                                >
                                    {status === "RUNNING" ? (
                                        <>
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            Running…
                                        </>
                                    ) : (
                                        <>
                                            <Play className="h-4 w-4" />
                                            Start Scraper
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h4 className="text-sm font-medium">Schedule</h4>
                            <div className="flex items-center justify-between text-sm text-muted-foreground border rounded-md p-3">
                                <span>Next scheduled run:</span>
                                <span className="font-mono">06:00 & 12:00 EAT</span>
                            </div>
                        </div>

                        {jobStatus && (
                            <div className="space-y-2">
                                <h4 className="text-sm font-medium">Latest Job</h4>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div className="rounded-md border p-2">
                                        <p className="text-muted-foreground">Found</p>
                                        <p className="font-semibold">{jobStatus.documents_found}</p>
                                    </div>
                                    <div className="rounded-md border p-2">
                                        <p className="text-muted-foreground">New</p>
                                        <p className="font-semibold">{jobStatus.documents_new}</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card className="flex flex-col h-[400px]">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div className="space-y-1.5">
                            <CardTitle>Live Logs</CardTitle>
                            <CardDescription>Output from scraper</CardDescription>
                        </div>
                        <Badge variant="outline" className="font-mono">v1.2.0</Badge>
                    </CardHeader>
                    <CardContent className="flex-1 p-0 relative">
                        <ScrollArea
                            className="h-full w-full rounded-md bg-black/90 p-4 font-mono text-xs text-green-400"
                            ref={scrollRef}
                        >
                            {logs.map((log, i) => (
                                <div key={i} className="mb-1">
                                    <span className="text-gray-500">[{log.timestamp}]</span>{" "}
                                    <span className={cn(
                                        log.level === "ERROR" ? "text-red-500"
                                            : log.level === "WARN" ? "text-yellow-500"
                                                : "text-blue-400"
                                    )}>{log.level}:</span>{" "}
                                    {log.message}
                                </div>
                            ))}
                            {status === "RUNNING" && <div className="animate-pulse">_</div>}
                        </ScrollArea>
                        <div className="absolute top-2 right-4">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-gray-400 hover:text-white"
                                onClick={() => setLogs(INITIAL_LOGS)}
                            >
                                <Terminal className="h-4 w-4" />
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
