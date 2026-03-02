'use client';

import React, { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Mail, Lock, Eye, EyeOff, User } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { customerAuthClient } from '@/lib/customer-auth-client';
import Link from 'next/link';

export function CustomerSignUpForm() {
    const t = useTranslations('auth');
    const locale = useLocale();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        const { error: signUpError } = await customerAuthClient.signUp.email({
            email,
            password,
            name,
        });

        if (signUpError) {
            setError(signUpError.message ?? 'An error occurred during sign up');
            setIsLoading(false);
            return;
        }

        router.push(`/${locale}/chat`); // Redirect to chat or home after signup
    };

    return (
        <Card className="w-full max-w-md backdrop-blur-md bg-background/80 supports-[backdrop-filter]:bg-background/40 border-muted/20 dark:border-white/20 shadow-xl">
            <CardHeader className="space-y-1 text-center">
                <CardTitle className="text-2xl font-bold tracking-tight">
                    Create an Account
                </CardTitle>
                <CardDescription>
                    Enter your details to get started
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <form onSubmit={handleSubmit}>
                    <div className="space-y-2">
                        <Label htmlFor="name">Full Name</Label>
                        <div className="relative">
                            <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="name"
                                type="text"
                                placeholder="John Doe"
                                className="pl-9"
                                disabled={isLoading}
                                required
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="space-y-2 mt-4">
                        <Label htmlFor="email">{t('email')}</Label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                className="pl-9"
                                disabled={isLoading}
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="space-y-2 mt-4">
                        <Label htmlFor="password">{t('password')}</Label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="password"
                                type={showPassword ? 'text' : 'password'}
                                className="pl-9 pr-10"
                                disabled={isLoading}
                                required
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

                    {error && (
                        <p className="text-sm text-destructive mt-2">{error}</p>
                    )}

                    <Button className="w-full mt-6" type="submit" disabled={isLoading}>
                        {isLoading ? t('processing') : 'Sign Up'}
                    </Button>
                </form>
            </CardContent>
            <CardFooter>
                <p className="text-sm text-center w-full text-muted-foreground">
                    Already have an account?{' '}
                    <Link href={`/${locale}/login`} className="text-primary hover:underline">
                        Sign in
                    </Link>
                </p>
            </CardFooter>
        </Card>
    );
}
