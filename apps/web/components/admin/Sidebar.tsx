"use client"

import { usePathname } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
    FileText,
    Database,
    Users,
    Settings,
    LogOut,
    ChevronLeft,
    Menu,
} from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { useLocale } from "next-intl"

export function AdminSidebar() {
    const pathname = usePathname()
    const locale = useLocale()
    const [isCollapsed, setIsCollapsed] = useState(false)

    const sidebarItems = [
        {
            title: "Overview",
            href: `/${locale}/admin`,
            icon: LayoutDashboard,
        },
        {
            title: "Knowledge Base",
            href: `/${locale}/admin/knowledge-base`,
            icon: FileText,
        },
        {
            title: "Scraper Control",
            href: `/${locale}/admin/scraper`,
            icon: Database,
        },
        {
            title: "Users",
            href: `/${locale}/admin/users`,
            icon: Users,
        },
        {
            title: "Settings",
            href: `/${locale}/admin/settings`,
            icon: Settings,
        },
    ]

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
                                <Icon className="h-4 w-4" />
                                {!isCollapsed && <span>{item.title}</span>}
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
                >
                    <LogOut className="h-4 w-4" />
                    {!isCollapsed && <span>Logout</span>}
                </Button>
            </div>
        </aside>
    )
}
