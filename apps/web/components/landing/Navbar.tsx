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
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export function Navbar() {
    const t = useTranslations('common');
    const authT = useTranslations('auth');
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const handleLanguageChange = (newLocale: string) => {
        const newPathname = pathname.replace(`/${locale}`, `/${newLocale}`);
        router.push(newPathname);
    };

    const navLinks = [
        { label: 'Features', href: '#features' },
        { label: 'How It Works', href: '#how-it-works' },
        { label: 'FAQ', href: '#faq' },
        { label: 'Pricing', href: '#pricing' },
    ];

    return (
        <header
            className={cn(
                'fixed top-0 left-0 right-0 z-50 flex justify-between items-center px-6 md:px-10 py-4 transition-all duration-300',
                scrolled
                    ? 'border-b border-white/[0.06] bg-background/80 backdrop-blur-xl'
                    : 'bg-transparent'
            )}
        >
            {/* Logo */}
            <Link href="/" className="flex items-center gap-1 group">
                <span className="text-xl font-bold tracking-tight text-foreground">Awaqi</span>
                <span className="text-xl font-bold text-muted-foreground/50 group-hover:text-muted-foreground transition-colors">.</span>
            </Link>

            {/* Center Navigation */}
            <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
                {navLinks.map(link => (
                    <Link
                        key={link.href}
                        href={link.href}
                        className="relative hover:text-foreground transition-colors duration-200 after:absolute after:bottom-0 after:left-0 after:h-px after:w-0 after:bg-foreground after:transition-all hover:after:w-full"
                    >
                        {link.label}
                    </Link>
                ))}
            </nav>

            {/* Right Actions */}
            <div className="flex items-center gap-3">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Change language"
                            className="text-muted-foreground hover:text-foreground h-8 w-8 rounded-full"
                        >
                            <Globe className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleLanguageChange('en')} disabled={locale === 'en'}>
                            {t('english')}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleLanguageChange('am')} disabled={locale === 'am'}>
                            {t('amharic')}
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                <ThemeToggle />

                <Button
                    asChild
                    size="sm"
                    className="hidden sm:flex h-8 px-5 rounded-full bg-foreground text-background hover:bg-foreground/90 font-medium text-sm transition-all"
                >
                    <Link href="/chat">Try Awaqi</Link>
                </Button>
            </div>
        </header>
    );
}
