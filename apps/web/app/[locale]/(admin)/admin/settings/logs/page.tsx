"use client"

import { useState, useEffect, useCallback } from "react"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Download, Search, Filter, Loader2, RefreshCw } from "lucide-react"
import { adminApi } from "@/lib/api"
import type { LogEntry } from "@/types/api"

export default function SystemLogsPage() {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [levelFilter, setLevelFilter] = useState("ALL")
    const [search, setSearch] = useState("")

    const fetchLogs = useCallback(async () => {
        setIsLoading(true)
        setError(null)
        try {
            const result = await adminApi.getLogs()
            setLogs(result.logs)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load logs")
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchLogs()
    }, [fetchLogs])

    const filtered = logs.filter((log) => {
        const matchesLevel = levelFilter === "ALL" || log.level === levelFilter
        const matchesSearch =
            !search ||
            log.message.toLowerCase().includes(search.toLowerCase()) ||
            log.timestamp.includes(search)
        return matchesLevel && matchesSearch
    })

    const handleExport = () => {
        const csv = [
            "Timestamp,Level,Message",
            ...filtered.map(
                (l) => `"${l.timestamp}","${l.level}","${l.message.replace(/"/g, '""')}"`
            ),
        ].join("\n")
        const blob = new Blob([csv], { type: "text/csv" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = "system-logs.csv"
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">System Logs</h1>
                <p className="text-muted-foreground">
                    Audit trails and system events for debugging and compliance.
                </p>
            </div>

            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <div className="relative w-64">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search logs…"
                            className="pl-8"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                    <Select value={levelFilter} onValueChange={setLevelFilter}>
                        <SelectTrigger className="w-[180px]">
                            <Filter className="mr-2 h-4 w-4 text-muted-foreground" />
                            <SelectValue placeholder="Filter by Level" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All Levels</SelectItem>
                            <SelectItem value="INFO">Info</SelectItem>
                            <SelectItem value="WARN">Warning</SelectItem>
                            <SelectItem value="ERROR">Error</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="gap-2" onClick={fetchLogs}>
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </Button>
                    <Button variant="outline" className="gap-2" onClick={handleExport} disabled={isLoading}>
                        <Download className="h-4 w-4" />
                        Export CSV
                    </Button>
                </div>
            </div>

            {error && (
                <p className="text-sm text-destructive">{error}</p>
            )}

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Timestamp</TableHead>
                            <TableHead>Level</TableHead>
                            <TableHead>Message</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow>
                                <TableCell colSpan={3} className="h-24 text-center">
                                    <Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" />
                                </TableCell>
                            </TableRow>
                        ) : filtered.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={3} className="h-24 text-center text-muted-foreground">
                                    No logs found.
                                </TableCell>
                            </TableRow>
                        ) : (
                            filtered.map((log, i) => (
                                <TableRow key={i}>
                                    <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                                        {log.timestamp}
                                    </TableCell>
                                    <TableCell>
                                        <Badge
                                            variant="outline"
                                            className={
                                                log.level === "ERROR"
                                                    ? "border-red-500 text-red-500"
                                                    : log.level === "WARN"
                                                        ? "border-yellow-500 text-yellow-500"
                                                        : "border-blue-500 text-blue-500"
                                            }
                                        >
                                            {log.level}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>{log.message}</TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    )
}
