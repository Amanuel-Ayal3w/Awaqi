'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';

export function BottomCTA() {
    return (
        <section className="py-32 relative overflow-hidden">
            {/* Radial glow */}
            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="w-[600px] h-[300px] bg-white/[0.03] blur-[100px] rounded-full" />
            </div>

            <div className="container relative z-10 flex flex-col items-center text-center">
                <h2 className="text-4xl md:text-6xl font-bold tracking-tight mb-6 max-w-3xl leading-[1.1]">
                    Built for Ethiopian Tax Compliance.
                    <br className="hidden md:block" />
                    <span className="text-muted-foreground/60">Available today.</span>
                </h2>

                <p className="text-muted-foreground text-lg max-w-xl mb-10 leading-relaxed">
                    Stop spending hours searching through tax regulations. Get precise, AI-powered answers instantly — in Amharic or English.
                </p>

                <div className="flex flex-col sm:flex-row gap-4">
                    <Button
                        asChild
                        size="lg"
                        className="h-12 px-8 rounded-full bg-foreground text-background hover:bg-foreground/90 font-semibold text-sm transition-all hover:scale-105"
                    >
                        <Link href="/chat">
                            Get Started Free
                            <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>
                    <Button
                        asChild
                        variant="ghost"
                        size="lg"
                        className="h-12 px-8 rounded-full border border-white/10 text-foreground hover:bg-white/5 font-medium text-sm transition-all"
                    >
                        <Link href="/contact">Contact Us</Link>
                    </Button>
                </div>
            </div>
        </section>
    );
}
