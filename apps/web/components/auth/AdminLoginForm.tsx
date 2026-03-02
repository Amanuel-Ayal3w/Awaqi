'use client';

import React, { useState } from 'react';
import { useLocale } from 'next-intl';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Mail, Lock, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { authClient } from '@/lib/auth-client';

export function AdminLoginForm() {
    const locale = useLocale();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        const { error: signInError } = await authClient.signIn.email({
            email,
            password,
        });

        if (signInError) {
            setError(signInError.message ?? 'Invalid email or password');
            setIsLoading(false);
            return;
        }

        router.push(`/${locale}/admin`);
    };

    return (
        <div className="flex flex-col items-center gap-6 w-full">
            {/* Admin badge */}
            <div className="flex flex-col items-center gap-2 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
                    <ShieldCheck className="h-7 w-7 text-primary" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight">Admin Portal</h1>
                <p className="text-sm text-muted-foreground max-w-xs">
                    Sign in with your administrator credentials to access the control panel.
                </p>
            </div>

            <Card className="w-full backdrop-blur-md bg-background/80 supports-[backdrop-filter]:bg-background/40 border-muted/20 dark:border-white/10 shadow-xl">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base font-semibold">Sign in</CardTitle>
                    <CardDescription className="text-xs">
                        Enter the credentials provided by your system administrator.
                    </CardDescription>
                </CardHeader>

                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Email */}
                        <div className="space-y-1.5">
                            <Label htmlFor="admin-email">Email address</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="admin-email"
                                    type="email"
                                    placeholder="admin@awaqi.io"
                                    className="pl-9"
                                    disabled={isLoading}
                                    required
                                    autoComplete="username"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div className="space-y-1.5">
                            <Label htmlFor="admin-password">Password</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="admin-password"
                                    type={showPassword ? 'text' : 'password'}
                                    className="pl-9 pr-10"
                                    disabled={isLoading}
                                    required
                                    autoComplete="current-password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                    onClick={() => setShowPassword(!showPassword)}
                                    disabled={isLoading}
                                    tabIndex={-1}
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                                    ) : (
                                        <Eye className="h-4 w-4 text-muted-foreground" />
                                    )}
                                    <span className="sr-only">
                                        {showPassword ? 'Hide password' : 'Show password'}
                                    </span>
                                </Button>
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <p className="text-sm text-destructive">{error}</p>
                        )}

                        <Button className="w-full" type="submit" disabled={isLoading}>
                            {isLoading ? 'Signing in…' : 'Sign in'}
                        </Button>
                    </form>
                </CardContent>

                <CardFooter className="flex-col gap-1 pt-0">
                    <div className="w-full border-t border-muted/30 pt-4">
                        <p className="text-xs text-center text-muted-foreground leading-relaxed">
                            Don&apos;t have access?{' '}
                            <span className="font-medium text-foreground/70">
                                Contact the system administrator
                            </span>{' '}
                            to obtain your credentials.
                        </p>
                    </div>
                </CardFooter>
            </Card>
        </div>
    );
}
