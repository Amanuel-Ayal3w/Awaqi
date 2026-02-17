'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { Twitter, Linkedin, Facebook, Github } from 'lucide-react';

export function Footer() {
    const t = useTranslations('landing');

    const socialLinks = [
        { icon: <Twitter className="h-4 w-4" />, href: "#" },
        { icon: <Linkedin className="h-4 w-4" />, href: "#" },
        { icon: <Facebook className="h-4 w-4" />, href: "#" },
        { icon: <Github className="h-4 w-4" />, href: "#" },
    ];

    return (
        <footer className="py-20 bg-background border-t border-white/5">
            <div className="container">
                <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-16">
                    <div className="col-span-2 md:col-span-2 pr-8">
                        <div className="flex items-center gap-2 mb-6">
                            <div className="h-6 w-6 rounded bg-primary flex items-center justify-center text-primary-foreground font-bold text-xs">A</div>
                            <span className="text-lg font-bold tracking-tight">Awaqi</span>
                        </div>
                        <p className="text-muted-foreground text-sm max-w-xs mb-8 leading-relaxed">
                            {t('heroSubtitle')}
                        </p>
                        <div className="flex gap-4">
                            {socialLinks.map((link, index) => (
                                <Link key={index} href={link.href} className="text-muted-foreground hover:text-foreground transition-colors p-2 hover:bg-white/5 rounded-full">
                                    {link.icon}
                                </Link>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h4 className="font-medium mb-6 text-sm text-foreground">{t('product')}</h4>
                        <ul className="space-y-4">
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('features')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('pricing')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('faq')}</Link></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-medium mb-6 text-sm text-foreground">{t('company')}</h4>
                        <ul className="space-y-4">
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('about')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('blog')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('contact')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">Customers</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="font-medium mb-6 text-sm text-foreground">Resources</h4>
                        <ul className="space-y-4">
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">Community</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">Help Center</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">Status</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="font-medium mb-6 text-sm text-foreground">Legal</h4>
                        <ul className="space-y-4">
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">{t('privacy')}</Link></li>
                            <li><Link href="#" className="text-muted-foreground hover:text-foreground transition-colors text-sm">Terms</Link></li>
                        </ul>
                    </div>
                </div>

                <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-muted-foreground">
                    <p>© {new Date().getFullYear()} Awaqi. All rights reserved.</p>
                    <div className="flex gap-8">
                        <Link href="#" className="hover:text-foreground">Privacy Policy</Link>
                        <Link href="#" className="hover:text-foreground">Terms of Service</Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
