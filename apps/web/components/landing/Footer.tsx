'use client';

import Link from 'next/link';
import { Twitter, Linkedin, Facebook, Github } from 'lucide-react';

const footerLinks = {
    Product: [
        { label: 'Features', href: '#features' },
        { label: 'How It Works', href: '#how-it-works' },
        { label: 'FAQ', href: '#faq' },
    ],
    Company: [
        { label: 'About Us', href: '/about' },
        { label: 'Contact', href: '/contact' },
        { label: 'Blog', href: '/blog' },
    ],
    Legal: [
        { label: 'Privacy Policy', href: '/privacy' },
        { label: 'Terms of Service', href: '/terms' },
    ],
};

const socialLinks = [
    { icon: <Twitter className="h-4 w-4" />, href: '#', label: 'Twitter' },
    { icon: <Linkedin className="h-4 w-4" />, href: '#', label: 'LinkedIn' },
    { icon: <Facebook className="h-4 w-4" />, href: '#', label: 'Facebook' },
    { icon: <Github className="h-4 w-4" />, href: '#', label: 'GitHub' },
];

export function Footer() {
    return (
        <footer className="py-16 border-t border-white/[0.06]">
            <div className="container">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-10 mb-14">
                    {/* Brand */}
                    <div className="col-span-2 pr-8">
                        <Link href="/" className="inline-flex items-center gap-1 mb-5">
                            <span className="text-lg font-bold tracking-tight">Awaqi</span>
                            <span className="text-lg font-bold text-muted-foreground/40">.</span>
                        </Link>
                        <p className="text-muted-foreground text-sm max-w-xs mb-6 leading-relaxed">
                            AI-powered Ethiopian tax support. Get accurate answers to your tax questions in Amharic and English, 24/7.
                        </p>
                        <div className="flex gap-3">
                            {socialLinks.map((link) => (
                                <Link
                                    key={link.label}
                                    href={link.href}
                                    aria-label={link.label}
                                    className="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-muted-foreground hover:text-foreground hover:border-white/30 transition-all duration-200"
                                >
                                    {link.icon}
                                </Link>
                            ))}
                        </div>
                    </div>

                    {/* Link columns */}
                    {Object.entries(footerLinks).map(([heading, links]) => (
                        <div key={heading}>
                            <h4 className="text-sm font-semibold text-foreground mb-5">{heading}</h4>
                            <ul className="space-y-3">
                                {links.map((link) => (
                                    <li key={link.label}>
                                        <Link
                                            href={link.href}
                                            className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200"
                                        >
                                            {link.label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                {/* Bottom bar */}
                <div className="pt-8 border-t border-white/[0.06] flex flex-col md:flex-row justify-between items-center gap-4">
                    <p className="text-xs text-muted-foreground">
                        © {new Date().getFullYear()} Awaqi. All rights reserved.
                    </p>
                    <p className="text-xs text-muted-foreground">
                        Ethiopian Revenue &amp; Customs Authority · Compliant AI
                    </p>
                </div>
            </div>
        </footer>
    );
}
