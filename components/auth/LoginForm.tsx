'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Mail, Phone, Lock, User, Chrome, Eye, EyeOff } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function LoginForm() {
    const t = useTranslations('auth');
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const toggleMode = () => setIsLogin(!isLogin);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        // Mock authentication
        setTimeout(() => {
            setIsLoading(false);
            router.push('/');
        }, 1500);
    };

    return (
        <Card className="w-full max-w-md backdrop-blur-md bg-background/80 supports-[backdrop-filter]:bg-background/40 border-muted/20 dark:border-white/20 shadow-xl">
            <CardHeader className="space-y-1 text-center">
                <CardTitle className="text-2xl font-bold tracking-tight">
                    {isLogin ? t('welcomeBack') : t('createAccount')}
                </CardTitle>
                <CardDescription>
                    {isLogin ? t('loginSubtitle') : t('signupSubtitle')}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <Button variant="outline" className="w-full relative" disabled={isLoading}>
                    <Chrome className="mr-2 h-4 w-4" />
                    {t('continueWithGoogle')}
                </Button>

                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground">
                            {t('orContinueWith')}
                        </span>
                    </div>
                </div>

                <Tabs defaultValue="email" className="w-full">
                    <TabsList className="grid w-full grid-cols-2 mb-4">
                        <TabsTrigger value="email">{t('email')}</TabsTrigger>
                        <TabsTrigger value="phone">{t('phone')}</TabsTrigger>
                    </TabsList>

                    <form onSubmit={handleSubmit}>
                        {!isLogin && (
                            <div className="space-y-2 mb-4">
                                <Label htmlFor="name">{t('fullName')}</Label>
                                <div className="relative">
                                    <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input id="name" placeholder="John Doe" className="pl-9" disabled={isLoading} />
                                </div>
                            </div>
                        )}

                        <TabsContent value="email" className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="email">{t('email')}</Label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input id="email" type="email" placeholder="m@example.com" className="pl-9" disabled={isLoading} required />
                                </div>
                            </div>
                        </TabsContent>
                        <TabsContent value="phone" className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="phone">{t('phone')}</Label>
                                <div className="relative">
                                    <Phone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input id="phone" type="tel" placeholder="+251 911 234 567" className="pl-9" disabled={isLoading} required />
                                </div>
                            </div>
                        </TabsContent>

                        <div className="space-y-2 mt-4">
                            <Label htmlFor="password">{t('password')}</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="password"
                                    type={showPassword ? "text" : "password"}
                                    className="pl-9 pr-10"
                                    disabled={isLoading}
                                    required
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
                                    <span className="sr-only">{showPassword ? 'Hide password' : 'Show password'}</span>
                                </Button>
                            </div>
                        </div>

                        <Button className="w-full mt-6" type="submit" disabled={isLoading}>
                            {isLoading ? t('processing') : (isLogin ? t('signIn') : t('signUp'))}
                        </Button>
                    </form>
                </Tabs>
            </CardContent>
            <CardFooter>
                <div className="text-sm text-center w-full text-muted-foreground">
                    {isLogin ? t('dontHaveAccount') : t('alreadyHaveAccount')}
                    {' '}
                    <button
                        onClick={toggleMode}
                        className="underline text-primary hover:text-primary/80 font-medium"
                        disabled={isLoading}
                    >
                        {isLogin ? t('signUp') : t('signIn')}
                    </button>
                </div>
            </CardFooter>
        </Card>
    );
}
