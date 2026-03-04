"use client"

import { User } from "lucide-react"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

import { ThemeToggle } from "@/components/layout/ThemeToggle"
import { authClient } from "@/lib/auth-client"
import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"

export function AdminHeader() {
    const { data: session } = authClient.useSession()
    const router = useRouter()
    const locale = useLocale()

    const user = session?.user
    const name = user?.name || user?.email || ""
    const initials = name
        .split(' ')
        .map(n => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()

    const handleLogout = async () => {
        await authClient.signOut()
        router.push(`/${locale}/admin/login`)
    }

    return (
        <header className="flex h-14 items-center gap-4 border-b bg-background px-6">
            <div className="flex flex-1 items-center justify-between">
                <h1 className="text-lg font-semibold">Dashboard</h1>
                <div className="flex items-center gap-4">
                    <ThemeToggle />
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="rounded-full">
                                {user ? (
                                    <Avatar className="h-8 w-8">
                                        <AvatarImage src={user.image || ""} alt={name} />
                                        <AvatarFallback className="bg-primary/10 text-primary">{initials}</AvatarFallback>
                                    </Avatar>
                                ) : (
                                    <User className="h-5 w-5" />
                                )}
                                <span className="sr-only">User menu</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuLabel>
                                {user ? (
                                    <div className="flex flex-col space-y-1">
                                        <p className="text-sm font-medium leading-none">{user.name || "Admin"}</p>
                                        <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
                                    </div>
                                ) : (
                                    "My Account"
                                )}
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="cursor-pointer" onClick={() => router.push(`/${locale}/admin/settings`)}>
                                Profile
                            </DropdownMenuItem>
                            <DropdownMenuItem className="cursor-pointer" onClick={() => router.push(`/${locale}/admin/settings`)}>
                                Settings
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-destructive cursor-pointer" onClick={handleLogout}>
                                Logout
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </header>
    )
}
