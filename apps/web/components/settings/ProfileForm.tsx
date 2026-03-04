'use client';

import React, { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
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
import { customerAuthClient } from '@/lib/customer-auth-client';
import { Loader2 } from 'lucide-react';

export function ProfileForm() {
    const t = useTranslations('settings');

    // Profile state
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [isProfileLoading, setProfileLoading] = useState(true);
    const [isSavingProfile, setSavingProfile] = useState(false);
    const [profileMessage, setProfileMessage] = useState({ text: '', type: '' });

    // Password state
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [isSavingPassword, setSavingPassword] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState({ text: '', type: '' });

    // Load initial session
    useEffect(() => {
        const loadSession = async () => {
            const { data } = await customerAuthClient.getSession();
            if (data?.user) {
                setName(data.user.name ?? '');
                setEmail(data.user.email);
            }
            setProfileLoading(false);
        };
        loadSession();
    }, []);

    const handleSaveProfile = async () => {
        setSavingProfile(true);
        setProfileMessage({ text: '', type: '' });

        const { error } = await customerAuthClient.updateUser({ name });

        if (error) {
            setProfileMessage({ text: error.message || 'Failed to update profile', type: 'error' });
        } else {
            setProfileMessage({ text: 'Profile updated successfully', type: 'success' });
        }
        setSavingProfile(false);
    };

    const handleChangePassword = async () => {
        setSavingPassword(true);
        setPasswordMessage({ text: '', type: '' });

        if (!currentPassword || !newPassword || !confirmPassword) {
            setPasswordMessage({ text: 'All fields are required', type: 'error' });
            setSavingPassword(false);
            return;
        }

        if (newPassword !== confirmPassword) {
            setPasswordMessage({ text: 'Passwords do not match', type: 'error' });
            setSavingPassword(false);
            return;
        }

        if (newPassword.length < 8) {
            setPasswordMessage({ text: 'Password must be at least 8 characters', type: 'error' });
            setSavingPassword(false);
            return;
        }

        const { error } = await customerAuthClient.changePassword({
            currentPassword,
            newPassword,
            revokeOtherSessions: true,
        });

        if (error) {
            setPasswordMessage({ text: error.message || 'Failed to change password', type: 'error' });
        } else {
            setPasswordMessage({ text: 'Password changed successfully', type: 'success' });
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        }
        setSavingPassword(false);
    };

    if (isProfileLoading) {
        return (
            <div className="flex justify-center items-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

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
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            disabled={isSavingProfile}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="email">{t('email')}</Label>
                        <Input id="email" value={email} disabled />
                    </div>

                    {profileMessage.text && (
                        <p className={`text-sm ${profileMessage.type === 'error' ? 'text-destructive' : 'text-green-600'}`}>
                            {profileMessage.text}
                        </p>
                    )}
                </CardContent>
                <CardFooter>
                    <Button onClick={handleSaveProfile} disabled={isSavingProfile || !name}>
                        {isSavingProfile && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {t('saveChanges')}
                    </Button>
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
                        <Input
                            id="currentPassword"
                            type="password"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            disabled={isSavingPassword}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="newPassword">{t('newPassword')}</Label>
                        <Input
                            id="newPassword"
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            disabled={isSavingPassword}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="confirmPassword">{t('confirmPassword')}</Label>
                        <Input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            disabled={isSavingPassword}
                        />
                    </div>

                    {passwordMessage.text && (
                        <p className={`text-sm ${passwordMessage.type === 'error' ? 'text-destructive' : 'text-green-600'}`}>
                            {passwordMessage.text}
                        </p>
                    )}
                </CardContent>
                <CardFooter>
                    <Button
                        variant="outline"
                        onClick={handleChangePassword}
                        disabled={isSavingPassword || !currentPassword || !newPassword || !confirmPassword}
                    >
                        {isSavingPassword && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {t('changePassword')}
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
