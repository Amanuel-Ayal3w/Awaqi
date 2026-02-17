'use client';

import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, Sparkles } from 'lucide-react';

export function Hero() {
    const t = useTranslations('landing');

    return (
        <section className="relative overflow-hidden pt-32 pb-20 md:pt-48 md:pb-32">
            {/* New "Spotlight" Background */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
                <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-primary/20 blur-[120px] rounded-[100%] opacity-40 animate-spotlight" />
                <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                {/* Stars/Dust effect could go here */}
            </div>

            <div className="container relative z-10 flex flex-col items-center text-center">
                <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary mb-8 backdrop-blur-xl animate-fade-in-up">
                    <Sparkles className="mr-2 h-3.5 w-3.5 text-primary" />
                    <span className="text-muted-foreground mr-1">Announcing</span> {t('newRelease')}
                    <ArrowRight className="ml-2 h-3 w-3 text-muted-foreground/50" />
                </div>

                <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-8 max-w-5xl bg-clip-text text-transparent bg-gradient-to-b from-foreground via-foreground/90 to-foreground/50 pb-2 dark:from-white dark:via-white/90 dark:to-white/50">
                    {t('heroTitle')}
                </h1>

                <p className="text-xl md:text-2xl text-muted-foreground max-w-2xl mb-12 leading-relaxed font-light">
                    {t('heroSubtitle')}
                </p>

                <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto mb-20">
                    <Button asChild size="lg" className="h-12 px-8 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 font-medium transition-all hover:scale-105">
                        <Link href="/login">
                            {t('getStarted')}
                            <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>
                    <Button asChild variant="outline" size="lg" className="h-12 px-8 rounded-full border-primary/20 bg-transparent hover:bg-primary/5 text-foreground backdrop-blur-sm transition-all hover:scale-105">
                        <Link href="/login">
                            {t('learnMore')}
                        </Link>
                    </Button>
                </div>

                {/* 3D Dashboard Preview Removed */}

            </div>
        </section>
    );
}
