"use client"

/**
 * JobProgress — SSE-powered real-time progress bar for background RQ jobs.
 *
 * Connects to GET /v1/admin/progress/{jobId} via Server-Sent Events and
 * displays an animated progress bar with the current step label.
 *
 * Usage:
 *   <JobProgress jobId="..." onDone={(status) => refresh()} />
 */

import { useCallback, useEffect, useRef, useState } from "react"
import { CheckCircle2, XCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { JobProgress as JobProgressData } from "@/types/api"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface JobProgressProps {
    jobId: string
    /** Called when the job reaches "done" or "failed" */
    onDone?: (finalStatus: "done" | "failed") => void
    className?: string
    /** Label shown above the bar while running (default: "Processing…") */
    label?: string
}

export function JobProgress({ jobId, onDone, className, label = "Processing…" }: JobProgressProps) {
    const [progress, setProgress] = useState<JobProgressData>({
        job_id: jobId,
        pct: 0,
        step: "Queued",
        status: "queued",
    })
    const evtRef = useRef<EventSource | null>(null)
    const onDoneRef = useRef(onDone)
    onDoneRef.current = onDone

    const connect = useCallback(async () => {
        if (evtRef.current) {
            evtRef.current.close()
        }

        // Build the SSE URL with the admin auth token attached as query param
        // so the EventSource (which doesn't support custom headers) can authenticate.
        // The FastAPI progress endpoint uses get_current_admin dep.
        let token: string | undefined
        try {
            const { authClient } = await import("@/lib/auth-client")
            const { data } = await authClient.getSession()
            token = data?.session?.token ?? undefined
        } catch {
            /* non-fatal */
        }

        const url = new URL(`${API_URL}/v1/admin/progress/${jobId}`)
        if (token) url.searchParams.set("token", token)

        const es = new EventSource(url.toString())
        evtRef.current = es

        es.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data) as JobProgressData
                setProgress(data)
                if (data.status === "done" || data.status === "failed") {
                    es.close()
                    onDoneRef.current?.(data.status)
                }
            } catch {
                /* ignore malformed events */
            }
        }

        es.onerror = () => {
            es.close()
        }
    }, [jobId])

    useEffect(() => {
        void connect()
        return () => {
            evtRef.current?.close()
        }
    }, [connect])

    const isDone = progress.status === "done"
    const isFailed = progress.status === "failed"
    const isRunning = progress.status === "running" || progress.status === "queued"

    return (
        <div className={cn("space-y-1.5", className)}>
            <div className="flex items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-1.5 font-medium">
                    {isRunning && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />}
                    {isDone && <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />}
                    {isFailed && <XCircle className="h-3.5 w-3.5 text-destructive" />}
                    {isDone ? "Complete" : isFailed ? "Failed" : label}
                </span>
                <span className="tabular-nums text-muted-foreground">{progress.pct}%</span>
            </div>

            {/* Progress bar */}
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                    className={cn(
                        "h-full rounded-full transition-all duration-500",
                        isDone && "bg-green-500",
                        isFailed && "bg-destructive",
                        isRunning && "bg-blue-500",
                    )}
                    style={{ width: `${progress.pct}%` }}
                />
            </div>

            {/* Step label */}
            {progress.step && (
                <p className="text-xs text-muted-foreground truncate">{progress.step}</p>
            )}
        </div>
    )
}
