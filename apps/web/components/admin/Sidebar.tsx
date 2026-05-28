"use client"

import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
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
    ChevronDown,
    ChevronRight,
    FolderTree,
    Upload,
    MessageSquare,
    GaugeCircle,
} from "lucide-react"
import { useEffect, useMemo, useState, type ComponentType } from "react"
import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useLocale } from "next-intl"
import { authClient } from "@/lib/auth-client"
import { adminApi } from "@/lib/api"

type FlatNavItem = {
    title: string
    href: string
    icon: ComponentType<{ className?: string }>
    badge: number | null
}

function pathMatches(href: string, pathname: string) {
    return pathname === href || pathname.startsWith(href + "/")
}

export function AdminSidebar() {
    const pathname = usePathname()
    const router = useRouter()
    const locale = useLocale()
    const [isCollapsed, setIsCollapsed] = useState(false)
    const { data: session } = authClient.useSession()
    const role = (session?.user as any)?.role as string | undefined
    const [reviewQueueCount, setReviewQueueCount] = useState<number>(0)

    const knowledgeBaseChildren = useMemo(
        () =>
            [
                {
                    title: "Telegram scraping",
                    href: `/${locale}/admin/telegram`,
                    icon: Send,
                },
                {
                    title: "Web scraping",
                    href: `/${locale}/admin/scraper`,
                    icon: Globe,
                },
                {
                    title: "Manual upload",
                    href: `/${locale}/admin/knowledge-base`,
                    icon: Upload,
                },
            ] as const,
        [locale]
    )

    const kbChildHrefs = useMemo(
        () => knowledgeBaseChildren.map((c) => c.href),
        [knowledgeBaseChildren]
    )

    const isKbChildActive = kbChildHrefs.some((href) => pathMatches(href, pathname))

    const [kbSectionOpen, setKbSectionOpen] = useState(isKbChildActive)

    useEffect(() => {
        if (isKbChildActive) setKbSectionOpen(true)
    }, [isKbChildActive])

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

    const flatNavItems = useMemo((): FlatNavItem[] => {
        const items: FlatNavItem[] = [
            {
                title: "Overview",
                href: `/${locale}/admin`,
                icon: LayoutDashboard,
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
                title: "Analytics",
                href: `/${locale}/admin/analytics`,
                icon: BarChart3,
                badge: null,
            },
            {
                title: "Evaluation",
                href: `/${locale}/admin/evaluation`,
                icon: GaugeCircle,
                badge: null,
            },
            {
                title: "Test chat",
                href: `/${locale}/admin/test-chat`,
                icon: MessageSquare,
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

    const renderFlatLink = (item: FlatNavItem, index: number) => {
        const Icon = item.icon
        const isActive = pathMatches(item.href, pathname)
        return (
            <Link
                key={`${item.href}-${index}`}
                href={item.href}
                className={cn(
                    "relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
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
    }

    const knowledgeBaseDropdown = (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className={cn(
                        "h-9 w-full shrink-0",
                        isKbChildActive && "bg-accent text-accent-foreground"
                    )}
                    aria-label="Knowledge base"
                >
                    <FolderTree className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="right" align="start" className="w-52">
                <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
                    Knowledge base
                </DropdownMenuLabel>
                {knowledgeBaseChildren.map((child) => {
                    const ChildIcon = child.icon
                    return (
                        <DropdownMenuItem key={child.href} asChild>
                            <Link href={child.href} className="cursor-pointer gap-2">
                                <ChildIcon className="h-4 w-4" />
                                {child.title}
                            </Link>
                        </DropdownMenuItem>
                    )
                })}
            </DropdownMenuContent>
        </DropdownMenu>
    )

    const knowledgeBaseExpanded = (
        <div className="grid gap-1">
            <button
                type="button"
                aria-expanded={kbSectionOpen}
                onClick={() => setKbSectionOpen(!kbSectionOpen)}
                className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                    isKbChildActive ? "bg-accent text-accent-foreground" : ""
                )}
            >
                <FolderTree className="h-4 w-4 shrink-0" />
                <span className="flex-1 truncate text-left">Knowledge base</span>
                {kbSectionOpen ? (
                    <ChevronDown className="h-4 w-4 shrink-0 opacity-70" />
                ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 opacity-70" />
                )}
            </button>
            {kbSectionOpen && (
                <div className="ml-2 grid gap-1 border-l border-border pl-2">
                    {knowledgeBaseChildren.map((child) => {
                        const ChildIcon = child.icon
                        const childActive = pathMatches(child.href, pathname)
                        return (
                            <Link
                                key={child.href}
                                href={child.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                                    childActive ? "bg-accent text-accent-foreground" : ""
                                )}
                            >
                                <ChildIcon className="h-4 w-4 shrink-0" />
                                <span className="flex-1 truncate">{child.title}</span>
                            </Link>
                        )
                    })}
                </div>
            )}
        </div>
    )

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
                    {renderFlatLink(flatNavItems[0], 0)}
                    {isCollapsed ? knowledgeBaseDropdown : knowledgeBaseExpanded}
                    {flatNavItems.slice(1).map((item, i) => renderFlatLink(item, i + 1))}
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
