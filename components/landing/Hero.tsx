'use client';

import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { ArrowRight, Sparkles } from 'lucide-react';

export function Hero() {
    const t = useTranslations('landing');

    return (
        <section className="relative overflow-hidden pt-20 pb-32 md:pt-32 md:pb-48">
            {/* Background Gradients */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full z-0 pointer-events-none">
                <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/20 rounded-full blur-[120px] opacity-50 dark:opacity-20" />
                <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-blue-500/20 rounded-full blur-[100px] opacity-30 dark:opacity-10" />
            </div>

            <div className="container relative z-10 flex flex-col items-center text-center">
                <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-sm font-medium text-primary mb-8 backdrop-blur-sm">
                    <Sparkles className="mr-2 h-3.5 w-3.5" />
                    {t('newRelease')}
                </div>

                <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6 max-w-4xl bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/70 dark:from-white dark:to-white/70">
                    {t('heroTitle')}
                </h1>

                <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed">
                    {t('heroSubtitle')}
                </p>

                <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
                    <Button asChild size="lg" className="text-md h-12 px-8 rounded-full shadow-lg shadow-primary/20 transition-all hover:shadow-primary/40 hover:scale-105">
                        <Link href="/login">
                            {t('getStarted')}
                            <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>
                    <Button asChild variant="outline" size="lg" className="text-md h-12 px-8 rounded-full border-primary/20 bg-background/50 backdrop-blur-sm hover:bg-background/80">
                        <Link href="/login">
                            {t('learnMore')}
                        </Link>
                    </Button>
                </div>
            </div>
        </section>
    );
}
