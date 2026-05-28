"use client"


import { useCallback, useEffect, useMemo, useState } from "react"
import { ColumnDef } from "@tanstack/react-table"
import { Filter, RefreshCw, Search, Trash2 } from "lucide-react"
import { adminApi } from "@/lib/api"
import type { AdminUserItem } from "@/types/api"
import { DataTable } from "@/components/ui/data-table"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { authClient } from "@/lib/auth-client"

type UserRow = {
    id: string
    name: string
    email: string
    role: string
    is_active: boolean
    created_at: string
}

export default function AdminUsersPage() {
    const { data: session } = authClient.useSession()
    const role = (session?.user as any)?.role as string | undefined
    const currentUserId = (session?.user as any)?.id as string | undefined
    const canCreateUser = role === "superadmin"

    const [users, setUsers] = useState<UserRow[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [createError, setCreateError] = useState<string | null>(null)
    const [deleteError, setDeleteError] = useState<string | null>(null)
    const [isCreating, setIsCreating] = useState(false)
    const [isDeletingUserId, setIsDeletingUserId] = useState<string | null>(null)
    const [patchingUserId, setPatchingUserId] = useState<string | null>(null)
    const [patchError, setPatchError] = useState<string | null>(null)
    const [userSearch, setUserSearch] = useState("")
    const [roleFilter, setRoleFilter] = useState<"all" | "editor" | "superadmin">("all")
    const [name, setName] = useState("")
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [newUserRole, setNewUserRole] = useState<"editor" | "superadmin">("editor")

    const mapUser = (user: AdminUserItem): UserRow => ({
        id: user.id,
        name: user.name ?? "",
        email: user.email,
        role: user.role,
        is_active: user.is_active,
        created_at: user.created_at,
    })

    const refreshUsers = useCallback(async () => {
        setIsRefreshing(true)
        setError(null)
        try {
            const result = await adminApi.listUsers()
            setUsers(result.users.map(mapUser))
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load users"
            setError(message)
        } finally {
            setIsLoading(false)
            setIsRefreshing(false)
        }
    }, [])

    useEffect(() => {
        void refreshUsers()
    }, [refreshUsers])

    const filteredUsers = useMemo(() => {
        let data = users
        if (roleFilter !== "all") data = data.filter((u) => u.role === roleFilter)
        if (userSearch.trim()) {
            const q = userSearch.toLowerCase()
            data = data.filter(
                (u) =>
                    u.email.toLowerCase().includes(q) ||
                    (u.name ?? "").toLowerCase().includes(q)
            )
        }
        return data
    }, [users, roleFilter, userSearch])

    const handleDeleteUser = async (userId: string) => {
        const shouldDelete = window.confirm("Delete this user?")
        if (!shouldDelete) {
            return
        }

        setDeleteError(null)
        setIsDeletingUserId(userId)
        try {
            await adminApi.deleteUser(userId)
            await refreshUsers()
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to delete user"
            setDeleteError(message)
        } finally {
            setIsDeletingUserId(null)
        }
    }

    const columns: ColumnDef<UserRow>[] = useMemo(
        () => [
            {
                accessorKey: "name",
                header: "Name",
                cell: ({ row }) => {
                    const value = row.getValue("name") as string
                    return <span className="font-medium">{value || "—"}</span>
                },
            },
            {
                accessorKey: "email",
                header: "Email",
                cell: ({ row }) => (
                    <span className="text-sm text-muted-foreground">{row.getValue("email") as string}</span>
                ),
            },
            {
                accessorKey: "role",
                header: "Role",
                cell: ({ row }) => {
                    const userId = row.original.id
                    const value = (row.getValue("role") as string).toLowerCase()
                    if (!canCreateUser) {
                        return <span className="capitalize">{value}</span>
                    }
                    return (
                        <Select
                            value={value}
                            disabled={patchingUserId === userId}
                            onValueChange={(v) => {
                                void (async () => {
                                    setPatchError(null)
                                    setPatchingUserId(userId)
                                    try {
                                        await adminApi.patchUser(userId, { role: v })
                                        await refreshUsers()
                                    } catch (err: unknown) {
                                        const message = err instanceof Error ? err.message : "Failed to update role"
                                        setPatchError(message)
                                    } finally {
                                        setPatchingUserId(null)
                                    }
                                })()
                            }}
                        >
                            <SelectTrigger className="h-8 w-[140px]">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="editor">Editor</SelectItem>
                                <SelectItem value="superadmin">Superadmin</SelectItem>
                            </SelectContent>
                        </Select>
                    )
                },
            },
            {
                accessorKey: "is_active",
                header: "Active",
                cell: ({ row }) => {
                    const userId = row.original.id
                    const isActive = row.getValue("is_active") as boolean
                    const isCurrentUser = currentUserId === userId
                    if (!canCreateUser) {
                        return (
                            <span
                                className={cn(
                                    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
                                    isActive
                                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                                        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                                )}
                            >
                                {isActive ? "Active" : "Inactive"}
                            </span>
                        )
                    }
                    return (
                        <Switch
                            checked={isActive}
                            disabled={isCurrentUser || patchingUserId === userId}
                            title={isCurrentUser ? "You cannot deactivate your own account" : undefined}
                            onCheckedChange={(checked) => {
                                void (async () => {
                                    setPatchError(null)
                                    setPatchingUserId(userId)
                                    try {
                                        await adminApi.patchUser(userId, { is_active: checked })
                                        await refreshUsers()
                                    } catch (err: unknown) {
                                        const message =
                                            err instanceof Error ? err.message : "Failed to update status"
                                        setPatchError(message)
                                    } finally {
                                        setPatchingUserId(null)
                                    }
                                })()
                            }}
                        />
                    )
                },
            },
            {
                accessorKey: "created_at",
                header: "Created",
                cell: ({ row }) => {
                    const value = row.getValue("created_at") as string
                    return (
                        <span className="text-xs text-muted-foreground">
                            {new Date(value).toLocaleString()}
                        </span>
                    )
                },
            },
            {
                id: "actions",
                header: "Actions",
                cell: ({ row }) => {
                    const userId = row.original.id
                    const isCurrentUser = currentUserId === userId
                    const isDeleting = isDeletingUserId === userId

                    return (
                        <div className="flex justify-end">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive"
                                onClick={() => void handleDeleteUser(userId)}
                                disabled={isCurrentUser || isDeleting}
                                title={isCurrentUser ? "You cannot delete your own account" : "Delete user"}
                            >
                                <Trash2 className={cn("h-4 w-4", isDeleting && "animate-pulse")} />
                            </Button>
                        </div>
                    )
                },
            },
        ],
        [canCreateUser, currentUserId, isDeletingUserId, patchingUserId, refreshUsers]
    )

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault()
        setCreateError(null)
        setIsCreating(true)

        const trimmedName = name.trim()
        const trimmedEmail = email.trim().toLowerCase()

        try {
            const result = await authClient.admin.createUser({
                name: trimmedName,
                email: trimmedEmail,
                password,
                role: newUserRole,
            })

            if (result.error) {
                setCreateError(result.error.message ?? "Failed to create user")
                return
            }

            setName("")
            setEmail("")
            setPassword("")
            setNewUserRole("editor")
            await refreshUsers()
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to create user"
            setCreateError(message)
        } finally {
            setIsCreating(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Users</h1>
                    <p className="text-muted-foreground">
                        Manage administrator accounts.
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => void refreshUsers()}
                    disabled={isRefreshing}
                >
                    <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
                    Refresh
                </Button>
            </div>

            {canCreateUser && (
                <form onSubmit={handleCreateUser} className="grid gap-4 rounded-lg border p-4 md:grid-cols-4">
                    <div className="space-y-2 md:col-span-1">
                        <Label htmlFor="new-user-name">Name</Label>
                        <Input
                            id="new-user-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Jane Doe"
                            required
                            disabled={isCreating}
                        />
                    </div>

                    <div className="space-y-2 md:col-span-1">
                        <Label htmlFor="new-user-email">Email</Label>
                        <Input
                            id="new-user-email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="jane@awaqi.io"
                            required
                            disabled={isCreating}
                        />
                    </div>

                    <div className="space-y-2 md:col-span-1">
                        <Label htmlFor="new-user-password">Password</Label>
                        <Input
                            id="new-user-password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            disabled={isCreating}
                        />
                    </div>

                    <div className="space-y-2 md:col-span-1">
                        <Label>Role</Label>
                        <Select
                            value={newUserRole}
                            onValueChange={(value) => setNewUserRole(value as "editor" | "superadmin")}
                            disabled={isCreating}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select role" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="editor">Editor</SelectItem>
                                <SelectItem value="superadmin">Superadmin</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="md:col-span-4 flex items-center justify-between gap-3">
                        <p className="text-xs text-muted-foreground">
                            Only superadmins can create admin users.
                        </p>
                        <Button type="submit" disabled={isCreating}>
                            {isCreating ? "Adding…" : "Add User"}
                        </Button>
                    </div>

                    {createError && (
                        <p className="md:col-span-4 text-sm text-destructive">{createError}</p>
                    )}
                </form>
            )}

            {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}
            {patchError && <p className="text-sm text-destructive">{patchError}</p>}

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 min-w-[200px] max-w-sm">
                    <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Search by name or email…"
                        value={userSearch}
                        onChange={(e) => setUserSearch(e.target.value)}
                        className="pl-8"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-muted-foreground" />
                    <Select value={roleFilter} onValueChange={(v) => setRoleFilter(v as "all" | "editor" | "superadmin")}>
                        <SelectTrigger className="w-[150px]">
                            <SelectValue placeholder="All roles" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All roles</SelectItem>
                            <SelectItem value="editor">Editor</SelectItem>
                            <SelectItem value="superadmin">Superadmin</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {error ? (
                <p className="text-sm text-destructive">{error}</p>
            ) : isLoading ? (
                <p className="text-sm text-muted-foreground">Loading users…</p>
            ) : (
                <DataTable columns={columns} data={filteredUsers} />
            )}
        </div>
    )
}
