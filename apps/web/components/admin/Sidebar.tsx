"use client"

import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
    FileText,
    Globe,
    Files,
    Send,
    BarChart3,
    Users,
    Settings,
    LogOut,
    ChevronLeft,
    Menu,
    ClipboardList,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { useLocale } from "next-intl"
import { authClient } from "@/lib/auth-client"
import { adminApi } from "@/lib/api"

export function AdminSidebar() {
    const pathname = usePathname()
    const router = useRouter()
    const locale = useLocale()
    const [isCollapsed, setIsCollapsed] = useState(false)
    const { data: session } = authClient.useSession()
    const role = (session?.user as any)?.role as string | undefined
    const [reviewQueueCount, setReviewQueueCount] = useState<number>(0)

    useEffect(() => {
        let cancelled = false
        const fetchCount = async () => {
            try {
                const result = await adminApi.listDocuments({
                    limit: 1,
                    status: "requires_manual_review",
                })
                if (!cancelled) setReviewQueueCount(result.total)
            } catch {
                // non-critical — badge simply won't show
            }
        }
        void fetchCount()
        const interval = setInterval(() => void fetchCount(), 60_000)
        return () => {
            cancelled = true
            clearInterval(interval)
        }
    }, [])

    const handleLogout = async () => {
        await authClient.signOut()
        router.push(`/${locale}/admin/login`)
    }

    const sidebarItems = useMemo(() => {
        const items = [
            {
                title: "Overview",
                href: `/${locale}/admin`,
                icon: LayoutDashboard,
                badge: null as number | null,
            },
            {
                title: "Knowledge Base",
                href: `/${locale}/admin/knowledge-base`,
                icon: FileText,
                badge: null,
            },
            {
                title: "Scraper",
                href: `/${locale}/admin/scraper`,
                icon: Globe,
                badge: null,
            },
            {
                title: "Documents",
                href: `/${locale}/admin/documents`,
                icon: Files,
                badge: null,
            },
            {
                title: "Review Queue",
                href: `/${locale}/admin/review-queue`,
                icon: ClipboardList,
                badge: reviewQueueCount > 0 ? reviewQueueCount : null,
            },
            {
                title: "Telegram",
                href: `/${locale}/admin/telegram`,
                icon: Send,
                badge: null,
            },
            {
                title: "Analytics",
                href: `/${locale}/admin/analytics`,
                icon: BarChart3,
                badge: null,
            },
        ]

        if (role === "superadmin") {
            items.push({
                title: "Users",
                href: `/${locale}/admin/users`,
                icon: Users,
                badge: null,
            })
        }

        items.push({
            title: "Settings",
            href: `/${locale}/admin/settings`,
            icon: Settings,
            badge: null,
        })

        return items
    }, [locale, role, reviewQueueCount])

    return (
        <aside
            className={cn(
                "relative flex flex-col border-r bg-background transition-all duration-300",
                isCollapsed ? "w-16" : "w-64"
            )}
        >
            <div className="flex h-14 items-center justify-between border-b px-4">
                {!isCollapsed && (
                    <span className="text-lg font-semibold tracking-tight">Admin</span>
                )}
                <Button
                    variant="ghost"
                    size="icon"
                    className="ml-auto h-8 w-8"
                    onClick={() => setIsCollapsed(!isCollapsed)}
                >
                    {isCollapsed ? (
                        <Menu className="h-4 w-4" />
                    ) : (
                        <ChevronLeft className="h-4 w-4" />
                    )}
                </Button>
            </div>
            <div className="flex-1 overflow-auto py-4">
                <nav className="grid gap-1 px-2">
                    {sidebarItems.map((item, index) => {
                        const Icon = item.icon
                        const isActive = pathname === item.href || pathname.startsWith(item.href + "/")
                        return (
                            <Link
                                key={index}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                                    isActive ? "bg-accent text-accent-foreground" : "transparent",
                                    isCollapsed && "justify-center px-2"
                                )}
                            >
                                <Icon className="h-4 w-4 shrink-0" />
                                {!isCollapsed && (
                                    <>
                                        <span className="flex-1">{item.title}</span>
                                        {item.badge != null && (
                                            <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[10px] font-bold text-destructive-foreground">
                                                {item.badge > 99 ? "99+" : item.badge}
                                            </span>
                                        )}
                                    </>
                                )}
                                {isCollapsed && item.badge != null && (
                                    <span className="absolute left-8 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[9px] font-bold text-destructive-foreground">
                                        {item.badge > 9 ? "9+" : item.badge}
                                    </span>
                                )}
                            </Link>
                        )
                    })}
                </nav>
            </div>
            <div className="border-t p-4">
                <Button
                    variant="ghost"
                    className={cn(
                        "w-full justify-start gap-3",
                        isCollapsed && "justify-center px-2"
                    )}
                    onClick={handleLogout}
                >
                    <LogOut className="h-4 w-4" />
                    {!isCollapsed && <span>Logout</span>}
                </Button>
            </div>
        </aside>
    )
}
