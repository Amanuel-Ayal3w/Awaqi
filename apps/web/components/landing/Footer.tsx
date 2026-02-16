'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { Twitter, Linkedin, Facebook, Github } from 'lucide-react';

export function Footer() {
    const t = useTranslations('landing');

    const socialLinks = [
        { icon: <Twitter className="h-5 w-5" />, href: "#" },
        { icon: <Linkedin className="h-5 w-5" />, href: "#" },
        { icon: <Facebook className="h-5 w-5" />, href: "#" },
        { icon: <Github className="h-5 w-5" />, href: "#" },
    ];

    return (
        <footer className="py-12 bg-background border-t border-border/40">
            <div className="container">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
                    <div className="col-span-1 md:col-span-2">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="h-8 w-8 rounded bg-primary flex items-center justify-center text-primary-foreground font-bold">A</div>
                            <span className="text-xl font-bold tracking-tight">Awaqi</span>
                        </div>
                        <p className="text-muted-foreground max-w-xs mb-6 leading-relaxed">
                            {t('heroSubtitle')}
                        </p>
                        <div className="flex gap-4">
                            {socialLinks.map((link, index) => (
                                <Link key={index} href={link.href} className="text-muted-foreground hover:text-foreground transition-colors">
                                    {link.icon}
                                </Link>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h4 className="font-semibold mb-4">{t('product')}</h4>
                        <ul className="space-y-2">
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('features')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('pricing')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('faq')}</Link></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-semibold mb-4">{t('company')}</h4>
                        <ul className="space-y-2">
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('about')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('blog')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('contact')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('privacy')}</Link></li>
                        </ul>
                    </div>
                </div>

                <div className="pt-8 border-t border-border/40 text-center text-sm text-muted-foreground">
                    © {new Date().getFullYear()} Awaqi. All rights reserved.
                </div>
            </div>
        </footer>
    );
}
