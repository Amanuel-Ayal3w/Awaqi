'use client';

import React from 'react';
import axios from 'axios';
import { adminApi } from '@/lib/api';
import { authClient } from '@/lib/auth-client';
import type { AdminUserItem } from '@/types/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';

export default function AdminUsersPage() {
    const { data: session, isPending } = authClient.useSession();
    const role = (session?.user as any)?.role as string | undefined;
    const router = useRouter();
    const locale = useLocale();

    React.useEffect(() => {
        if (!isPending && role && role !== 'superadmin') {
            router.replace(`/${locale}/admin`);
        }
    }, [isPending, role, router, locale]);

    const [users, setUsers] = React.useState<AdminUserItem[]>([]);
    const [isLoading, setIsLoading] = React.useState(true);
    const [isCreating, setIsCreating] = React.useState(false);
    const [deletingUserId, setDeletingUserId] = React.useState<string | null>(null);
    const [error, setError] = React.useState<string | null>(null);
    const [debugInfo, setDebugInfo] = React.useState<string | null>(null);

    const [name, setName] = React.useState('');
    const [email, setEmail] = React.useState('');
    const [password, setPassword] = React.useState('');

    const loadUsers = React.useCallback(async () => {
        setIsLoading(true);
        setError(null);
        setDebugInfo(null);
        try {
            const data = await adminApi.listUsers();
            setUsers(data.users);
        } catch (err: unknown) {
            let detail: string | undefined;

            if (axios.isAxiosError(err)) {
                detail = err.response?.data?.detail as string | undefined;

                const debugPayload = {
                    message: err.message,
                    code: err.code,
                    status: err.response?.status,
                    method: err.config?.method,
                    url: err.config?.url,
                    baseURL: err.config?.baseURL,
                    responseData: err.response?.data,
                };

                setDebugInfo(JSON.stringify(debugPayload, null, 2));
                console.warn('adminApi.listUsers failed', debugPayload);
            } else {
                setDebugInfo(String(err));
                console.warn('adminApi.listUsers failed (non-axios error)', err);
            }

            setError(detail ?? 'Failed to load users.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    React.useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    const handleCreateUser = async (event: React.FormEvent) => {
        event.preventDefault();
        setIsCreating(true);
        setError(null);

        try {
            const response = await fetch('/api/auth/sign-up/email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'omit',
                body: JSON.stringify({
                    name,
                    email,
                    password,
                }),
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                const message = payload?.message ?? payload?.error ?? 'Failed to create user.';
                throw new Error(message);
            }

            setName('');
            setEmail('');
            setPassword('');
            await loadUsers();
        } catch (createError) {
            if (createError instanceof Error) {
                setError(createError.message);
            } else {
                setError('Failed to create user.');
            }
        } finally {
            setIsCreating(false);
        }
    };

    const handleDeleteUser = async (userId: string) => {
        setDeletingUserId(userId);
        setError(null);
        try {
            await adminApi.deleteUser(userId);
            await loadUsers();
        } catch {
            setError('Failed to remove user.');
        } finally {
            setDeletingUserId(null);
        }
    };

    if (isPending || role !== 'superadmin') {
        return null;
    }

    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
                <p className="text-muted-foreground">
                    Add, view, and remove admin users.
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Add Admin User</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleCreateUser} className="grid gap-4 md:grid-cols-3">
                        <div className="space-y-2">
                            <Label htmlFor="user-name">Name</Label>
                            <Input
                                id="user-name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Admin Name"
                                required
                                disabled={isCreating}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="user-email">Email</Label>
                            <Input
                                id="user-email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="admin@awaqi.io"
                                required
                                disabled={isCreating}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="user-password">Password</Label>
                            <Input
                                id="user-password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                disabled={isCreating}
                            />
                        </div>

                        <div className="md:col-span-3 flex justify-end">
                            <Button type="submit" disabled={isCreating}>
                                {isCreating ? 'Creating...' : 'Add User'}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Admin Users ({users.length})</CardTitle>
                </CardHeader>
                <CardContent>
                    {error && (
                        <div className="mb-3 space-y-3">
                            <div className="flex items-center justify-between gap-3">
                                <p className="text-sm text-destructive">{error}</p>
                                <Button variant="outline" size="sm" onClick={loadUsers}>
                                    Retry
                                </Button>
                            </div>
                            {debugInfo && (
                                <pre className="text-xs bg-muted/50 border rounded-md p-3 overflow-auto">
                                    {debugInfo}
                                </pre>
                            )}
                        </div>
                    )}

                    {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading users...</p>
                    ) : !error && users.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No users found.</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-left">
                                        <th className="py-2 pr-4 font-medium">Name</th>
                                        <th className="py-2 pr-4 font-medium">Email</th>
                                        <th className="py-2 pr-4 font-medium">Role</th>
                                        <th className="py-2 pr-4 font-medium">Status</th>
                                        <th className="py-2 pr-4 font-medium">Created</th>
                                        <th className="py-2 text-right font-medium">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.map((user) => (
                                        <tr key={user.id} className="border-b">
                                            <td className="py-2 pr-4">{user.name || '-'}</td>
                                            <td className="py-2 pr-4">{user.email}</td>
                                            <td className="py-2 pr-4">{user.role}</td>
                                            <td className="py-2 pr-4">{user.is_active ? 'active' : 'inactive'}</td>
                                            <td className="py-2 pr-4">{new Date(user.created_at).toLocaleString()}</td>
                                            <td className="py-2 text-right">
                                                <Button
                                                    variant="destructive"
                                                    size="sm"
                                                    onClick={() => handleDeleteUser(user.id)}
                                                    disabled={deletingUserId === user.id}
                                                >
                                                    {deletingUserId === user.id ? 'Removing...' : 'Remove'}
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
