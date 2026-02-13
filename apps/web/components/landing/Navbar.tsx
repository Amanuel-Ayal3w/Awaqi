'use client';

import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';

export function Navbar() {
    const t = useTranslations('common');
    const authT = useTranslations('auth'); // Access auth translations for "Sign In"
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();

    const handleLanguageChange = (newLocale: string) => {
        const newPathname = pathname.replace(`/${locale}`, `/${newLocale}`);
        router.push(newPathname);
    };

    return (
        <header className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center px-6 py-4 bg-background/50 backdrop-blur-md border-b border-white/5 supports-[backdrop-filter]:bg-background/20">
            {/* Logo area */}
            <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded bg-primary flex items-center justify-center text-primary-foreground font-bold">A</div>
                <span className="text-lg font-bold tracking-tight">{t('appName')}</span>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-4">
                {/* Language Toggle */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" aria-label="Change language">
                            <Globe className="h-[1.2rem] w-[1.2rem]" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem
                            onClick={() => handleLanguageChange('en')}
                            disabled={locale === 'en'}
                        >
                            {t('english')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => handleLanguageChange('am')}
                            disabled={locale === 'am'}
                        >
                            {t('amharic')}
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* Theme Toggle */}
                <ThemeToggle />

                {/* Login Button */}
                <Button asChild size="sm" className="hidden sm:flex rounded-full px-6">
                    <Link href="/login">
                        {authT('signIn')}
                    </Link>
                </Button>
            </div>
        </header>
    );
}
