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
        <header className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center px-6 py-4 border-b border-white/5 bg-background/60 backdrop-blur-xl supports-[backdrop-filter]:bg-background/20">
            {/* Logo area */}
            <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded bg-primary flex items-center justify-center text-primary-foreground font-bold shadow-[0_0_15px_rgba(255,255,255,0.3)]">A</div>
                <span className="text-xl font-bold tracking-tight">Awaqi</span>
            </div>

            {/* Center Navigation (Optional - Linear style often has this) */}
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-muted-foreground">
                <Link href="#" className="hover:text-foreground transition-colors">Features</Link>
                <Link href="#" className="hover:text-foreground transition-colors">Method</Link>
                <Link href="#" className="hover:text-foreground transition-colors">Customers</Link>
                <Link href="#" className="hover:text-foreground transition-colors">Changelog</Link>
                <Link href="#" className="hover:text-foreground transition-colors">Pricing</Link>
            </nav>

            {/* Right Actions */}
            <div className="flex items-center gap-4">
                {/* Language Toggle */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" aria-label="Change language" className="text-muted-foreground hover:text-foreground">
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

                {/* Theme Toggle - Removed to enforce dark mode vibe or keep if needed, keeping for now */}
                <ThemeToggle />

                {/* Login Button */}
                <Button asChild size="sm" className="hidden sm:flex rounded-full px-6 bg-foreground/5 hover:bg-foreground/10 text-foreground border border-foreground/10 dark:bg-white/10 dark:text-white dark:border-white/5 backdrop-blur-sm transition-all">
                    <Link href="/login">
                        {authT('signIn')}
                    </Link>
                </Button>
            </div>
        </header>
    );
}
