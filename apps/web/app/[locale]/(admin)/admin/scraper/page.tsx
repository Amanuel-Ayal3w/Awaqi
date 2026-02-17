"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Play, Square, Loader2, Terminal, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

type LogEntry = {
    timestamp: string
    level: "INFO" | "WARN" | "ERROR"
    message: string
}

const initialLogs: LogEntry[] = [
    { timestamp: "10:00:01", level: "INFO", message: "Scraper service initialized" },
    { timestamp: "10:00:02", level: "INFO", message: "Connected to database" },
    { timestamp: "10:00:05", level: "INFO", message: "Checked mor.gov.et for updates" },
    { timestamp: "10:00:06", level: "INFO", message: "No new documents found" },
    { timestamp: "10:00:07", level: "INFO", message: "Scraping cycle completed" },
]

export default function ScraperControlPage() {
    const [status, setStatus] = useState<"IDLE" | "RUNNING" | "STOPPING">("IDLE")
    const [logs, setLogs] = useState<LogEntry[]>(initialLogs)
    const [duration, setDuration] = useState(0)
    const scrollRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        let interval: NodeJS.Timeout
        if (status === "RUNNING") {
            interval = setInterval(() => {
                setDuration((prev) => prev + 1)
                // Simulate logs
                if (Math.random() > 0.7) {
                    const newLog: LogEntry = {
                        timestamp: new Date().toLocaleTimeString(),
                        level: Math.random() > 0.9 ? "WARN" : "INFO",
                        message: `Scraping page ${Math.floor(Math.random() * 100)}...`
                    }
                    setLogs(prev => [...prev, newLog])
                }
            }, 1000)
        } else {
            setDuration(0)
        }
        return () => clearInterval(interval)
    }, [status])

    // Auto-scroll to bottom of logs
    useEffect(() => {
        if (scrollRef.current) {
            const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollContainer) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    }, [logs]);


    const handleStart = () => {
        setStatus("RUNNING")
        setLogs(prev => [...prev, { timestamp: new Date().toLocaleTimeString(), level: "INFO", message: "Manual scrape triggered by admin" }])
    }

    const handleStop = () => {
        setStatus("STOPPING")
        setTimeout(() => {
            setStatus("IDLE")
            setLogs(prev => [...prev, { timestamp: new Date().toLocaleTimeString(), level: "WARN", message: "Scraper stopped by user" }])
        }, 1500)
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Scraper Control</h1>
                <p className="text-muted-foreground">
                    Monitor and control the improved web scraping service.
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Status</CardTitle>
                        <CardDescription>Current state of the scraper service</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div className="flex items-center gap-4">
                                <div className={cn(
                                    "relative flex h-3 w-3",
                                    status === "RUNNING" && "animate-pulse"
                                )}>
                                    <span className={cn(
                                        "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                                        status === "RUNNING" ? "bg-green-400" : "hidden"
                                    )}></span>
                                    <span className={cn(
                                        "relative inline-flex rounded-full h-3 w-3",
                                        status === "RUNNING" ? "bg-green-500" : status === "IDLE" ? "bg-gray-400" : "bg-yellow-500"
                                    )}></span>
                                </div>
                                <div className="space-y-1">
                                    <p className="font-medium leading-none">
                                        {status === "RUNNING" ? "Running" : status === "IDLE" ? "Idle" : "Stopping..."}
                                    </p>
                                    {status === "RUNNING" && (
                                        <p className="text-sm text-muted-foreground">Duration: {duration}s</p>
                                    )}
                                </div>
                            </div>
                            <div className="flex gap-2">
                                {status === "IDLE" ? (
                                    <Button onClick={handleStart} className="gap-2">
                                        <Play className="h-4 w-4" /> Start Scraper
                                    </Button>
                                ) : (
                                    <Button variant="destructive" onClick={handleStop} disabled={status === "STOPPING"} className="gap-2">
                                        {status === "STOPPING" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
                                        Stop
                                    </Button>
                                )}
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h4 className="text-sm font-medium">Schedule</h4>
                            <div className="flex items-center justify-between text-sm text-muted-foreground border rounded-md p-3">
                                <span>Next scheduled run:</span>
                                <span className="font-mono">Tomorrow, 00:00 EAT</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="flex flex-col h-[400px]">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div className="space-y-1.5">
                            <CardTitle>Live Logs</CardTitle>
                            <CardDescription>Real-time output from scraper</CardDescription>
                        </div>
                        <Badge variant="outline" className="font-mono">v1.2.0</Badge>
                    </CardHeader>
                    <CardContent className="flex-1 p-0 relative">
                        <ScrollArea className="h-full w-full rounded-md bg-black/90 p-4 font-mono text-xs text-green-400" ref={scrollRef}>
                            {logs.map((log, i) => (
                                <div key={i} className="mb-1">
                                    <span className="text-gray-500">[{log.timestamp}]</span>{" "}
                                    <span className={cn(
                                        log.level === "ERROR" ? "text-red-500" : log.level === "WARN" ? "text-yellow-500" : "text-blue-400"
                                    )}>{log.level}:</span>{" "}
                                    {log.message}
                                </div>
                            ))}
                            {status === "RUNNING" && (
                                <div className="animate-pulse">_</div>
                            )}
                        </ScrollArea>
                        <div className="absolute top-2 right-4">
                            <Button variant="ghost" size="icon" className="h-6 w-6 text-gray-400 hover:text-white" onClick={() => setLogs(initialLogs)}>
                                <Terminal className="h-4 w-4" />
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
