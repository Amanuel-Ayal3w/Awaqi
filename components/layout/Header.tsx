'use client';

import React from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { ThemeToggle } from './ThemeToggle';
import { Globe, Menu } from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';

export function Header() {
    const t = useTranslations('common');
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();
    const { toggleMobileOpen } = useSidebar();

    const handleLanguageChange = (newLocale: string) => {
        // Replace the locale in the current pathname
        const newPathname = pathname.replace(`/${locale}`, `/${newLocale}`);
        router.push(newPathname);
    };

    return (
        <header className="flex justify-between items-center px-4 py-3 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 border-b sticky top-0 z-40">
            {/* Left Section: Title Only (Sidebar handle toggle) */}
            <div className="flex items-center gap-2">

                {/* Mobile Toggle - Visible only on mobile */}
                <Button
                    variant="ghost"
                    size="icon"
                    className="md:hidden"
                    onClick={toggleMobileOpen}
                    aria-label="Open menu"
                >
                    <Menu className="h-5 w-5" />
                </Button>

                <h1 className="text-lg font-semibold text-foreground hidden md:block">{t('appName')}</h1>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-2">
                {/* Language Toggle */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="icon" aria-label="Change language">
                            <Globe className="h-[1.2rem] w-[1.2rem]" />
                            <span className="sr-only">{t('language')}</span>
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
            </div>
        </header>
    );
}
