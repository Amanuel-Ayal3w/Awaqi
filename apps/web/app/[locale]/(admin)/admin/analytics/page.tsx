"use client"

import { useCallback, useEffect, useState } from "react"
import { adminApi } from "@/lib/api"
import type { AdminAnalytics } from "@/types/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

export default function AdminAnalyticsPage() {
    const [data, setData] = useState<AdminAnalytics | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [refreshing, setRefreshing] = useState(false)

    const load = useCallback(async () => {
        setRefreshing(true)
        setError(null)
        try {
            const a = await adminApi.getAnalytics()
            setData(a)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load analytics")
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
        <div className="space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
                    <p className="text-muted-foreground">
                        Live counts from the API: documents, chunks, users, sessions, and messages.
                    </p>
                </div>
                <Button variant="outline" size="sm" className="gap-2" onClick={() => void load()} disabled={refreshing}>
                    <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            {loading && !data ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : data ? (
                <>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Documents</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.documents_total}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Chunks</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.chunks_total}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Admin users</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.admin_users_total}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Customer users</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.customer_users_total}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Chat sessions</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.chat_sessions_total}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Messages (all time)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.messages_total}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium">Messages (7 days)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{data.messages_last_7_days}</div>
                            </CardContent>
                        </Card>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                        <Card>
                            <CardHeader>
                                <CardTitle>Documents by status</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="h-[320px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={chartData} margin={{ left: 4, right: 8 }}>
                                            <XAxis
                                                dataKey="name"
                                                tick={{ fontSize: 11 }}
                                                interval={0}
                                                angle={-25}
                                                textAnchor="end"
                                                height={70}
                                            />
                                            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: "var(--background)",
                                                    borderColor: "var(--border)",
                                                }}
                                            />
                                            <Bar dataKey="count" name="Count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                <CardTitle>Status breakdown</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2 text-sm">
                                    {data.documents_by_status.map((row) => (
                                        <li key={row.status} className="flex justify-between border-b border-border/60 py-1">
                                            <span className="text-muted-foreground">{row.status}</span>
                                            <span className="font-mono font-medium">{row.count}</span>
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>
                        </Card>
                    </div>
                </>
            ) : null}
        </div>
    )
}
