'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

export function ProfileForm() {
    const t = useTranslations('settings');
    const tAuth = useTranslations('auth');

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>{t('profileInfo')}</CardTitle>
                    <CardDescription>Update your personal information.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">{t('name')}</Label>
                        <Input id="name" defaultValue="Amanuel Ayalew" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="email">{t('email')}</Label>
                        <Input id="email" defaultValue="amanuel@example.com" disabled />
                    </div>
                </CardContent>
                <CardFooter>
                    <Button>{t('saveChanges')}</Button>
                </CardFooter>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>{t('changePassword')}</CardTitle>
                    <CardDescription>Ensure your account is secure using a long, random password.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="currentPassword">{t('currentPassword')}</Label>
                        <Input id="currentPassword" type="password" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="newPassword">{t('newPassword')}</Label>
                        <Input id="newPassword" type="password" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="confirmPassword">{t('confirmPassword')}</Label>
                        <Input id="confirmPassword" type="password" />
                    </div>
                </CardContent>
                <CardFooter>
                    <Button variant="outline">{t('changePassword')}</Button>
                </CardFooter>
            </Card>
        </div>
    );
}
