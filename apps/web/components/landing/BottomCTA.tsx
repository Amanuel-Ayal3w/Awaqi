'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';

export function BottomCTA() {
    return (
        <section className="py-32 relative overflow-hidden flex flex-col items-center justify-center text-center">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-primary/5 pointer-events-none" />

            <h2 className="text-4xl md:text-6xl font-bold tracking-tight mb-8 max-w-3xl bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/50">
                Built for the future. <br className="hidden md:block" /> Available today.
            </h2>

            <div className="flex flex-col sm:flex-row gap-4 mb-12 relative z-10">
                <Button asChild size="lg" className="h-12 px-8 rounded-full bg-foreground text-background hover:bg-foreground/90 font-medium transition-all hover:scale-105">
                    <Link href="/login">
                        Get Started
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                </Button>
                <Button asChild variant="ghost" size="lg" className="h-12 px-8 rounded-full text-foreground hover:bg-foreground/5 transition-all">
                    <Link href="/contact">
                        Contact Sales
                    </Link>
                </Button>
            </div>

        </section>
    );
}
