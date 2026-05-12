"use client"

import { useCallback, useEffect, useState } from "react"
import { adminApi } from "@/lib/api"
import type { AdminAnalytics, AdminSystemHealth } from "@/types/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { useLocale } from "next-intl"
import { FileText, Database, Users, MessageSquare, RefreshCw, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

export default function AdminDashboard() {
    const locale = useLocale()
    const [data, setData] = useState<AdminAnalytics | null>(null)
    const [health, setHealth] = useState<AdminSystemHealth | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [refreshing, setRefreshing] = useState(false)

    const load = useCallback(async () => {
        setRefreshing(true)
        setError(null)
        try {
            const [analyticsResult, healthResult] = await Promise.allSettled([
                adminApi.getAnalytics(),
                adminApi.getSystemHealth(),
            ])
            if (analyticsResult.status === "fulfilled") {
                setData(analyticsResult.value)
            } else {
                setData(null)
                const reason =
                    analyticsResult.reason instanceof Error
                        ? analyticsResult.reason.message
                        : "Failed to load dashboard data"
                setError(reason)
            }
            if (healthResult.status === "fulfilled") {
                setHealth(healthResult.value)
            } else {
                setHealth(null)
            }
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => {
        void load()
    }, [load])

    const chartData =
        data?.documents_by_status.map((d) => ({
            name: d.status.replace(/_/g, " "),
            count: d.count,
        })) ?? []

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">Overview from live analytics. Open Analytics for more detail.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="gap-2" onClick={() => void load()} disabled={refreshing}>
                        <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
                        Refresh
                    </Button>
                    <Button variant="secondary" size="sm" asChild>
                        <Link href={`/${locale}/admin/analytics`}>Full analytics</Link>
                    </Button>
                </div>
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            {health ? (
                <div className="grid gap-4 md:grid-cols-2">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">PostgreSQL</CardTitle>
                            <Activity className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <p
                                className={cn(
                                    "text-sm font-semibold",
                                    health.database_ok ? "text-emerald-600 dark:text-emerald-500" : "text-destructive"
                                )}
                            >
                                {health.database_ok ? "Reachable" : "Unreachable"}
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Redis</CardTitle>
                            <Activity className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <p
                                className={cn(
                                    "text-sm font-semibold",
                                    health.redis_ok ? "text-emerald-600 dark:text-emerald-500" : "text-destructive"
                                )}
                            >
                                {health.redis_ok
                                    ? `Reachable${
                                          health.redis_latency_ms != null
                                              ? ` · ${health.redis_latency_ms.toFixed(1)} ms`
                                              : ""
                                      }`
                                    : "Unreachable"}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            ) : null}

            {loading && !data ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : data ? (
                <>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Documents</CardTitle>
                                <FileText className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.documents_total}</div>
                                <p className="text-xs text-muted-foreground">Indexed + in pipeline</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Chunks</CardTitle>
                                <Database className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.chunks_total}</div>
                                <p className="text-xs text-muted-foreground">Vector index size</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Customer users</CardTitle>
                                <Users className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.customer_users_total}</div>
                                <p className="text-xs text-muted-foreground">Chat accounts</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Messages (7d)</CardTitle>
                                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.messages_last_7_days}</div>
                                <p className="text-xs text-muted-foreground">Of {data.messages_total} all-time</p>
                            </CardContent>
                        </Card>
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle>Documents by status</CardTitle>
                        </CardHeader>
                        <CardContent className="h-[300px] pl-0">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData} margin={{ left: 8, right: 8, bottom: 8 }}>
                                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={56} />
                                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "var(--background)",
                                            borderColor: "var(--border)",
                                        }}
                                    />
                                    <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </>
            ) : null}
        </div>
    )
}
