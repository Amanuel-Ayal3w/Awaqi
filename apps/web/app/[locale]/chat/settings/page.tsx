'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { ProfileForm } from '@/components/settings/ProfileForm';

export default function SettingsPage() {
    const t = useTranslations('settings');

    return (
        <div className="container max-w-4xl py-6 lg:py-10 space-y-8">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
                <p className="text-muted-foreground">
                    Manage your account settings and profile information.
                </p>
            </div>

            <div className="space-y-6">
                <ProfileForm />
            </div>
        </div>
    );
}
