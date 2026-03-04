'use client';

import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { ArrowRight, Globe, Clock, Zap, ShieldCheck } from 'lucide-react';

function AnimatedWaveform() {
    return (
        <div className="w-full max-w-sm mx-auto my-8 opacity-70">
            <svg
                viewBox="0 0 300 50"
                xmlns="http://www.w3.org/2000/svg"
                className="w-full h-12"
                aria-hidden="true"
            >
                <path
                    className="waveform-path"
                    d="M0,25 C20,10 40,40 60,25 S100,10 120,25 S160,40 180,25 S220,10 240,25 S280,40 300,25"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                />
            </svg>
        </div>
    );
}

const pills = [
    { icon: <Globe className="h-3.5 w-3.5" />, label: 'Amharic & English' },
    { icon: <Clock className="h-3.5 w-3.5" />, label: '24/7 Available' },
    { icon: <Zap className="h-3.5 w-3.5" />, label: 'Instant Answers' },
    { icon: <ShieldCheck className="h-3.5 w-3.5" />, label: 'Secure' },
];

export function Hero() {
    const t = useTranslations('landing');

    return (
        <section className="relative overflow-hidden pt-36 pb-24 md:pt-52 md:pb-36">
            {/* Subtle spotlight glow */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
                <div className="absolute top-[-5%] left-1/2 -translate-x-1/2 w-[900px] h-[450px] bg-white/5 blur-[140px] rounded-[100%] animate-spotlight" />
                <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            </div>

            <div className="container relative z-10 flex flex-col items-center text-center">
                {/* Sub-label */}
                <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-muted-foreground mb-10 backdrop-blur-sm animate-fade-in-up">
                    Ethiopian Revenue Authority · AI-Powered Support
                </div>

                {/* Main headline */}
                <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-6 max-w-4xl leading-[1.05]">
                    {t('heroTitle')}
                </h1>

                {/* Sub-headline */}
                <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed font-normal">
                    {t('heroSubtitle')}
                </p>

                {/* Feature pills */}
                <div className="flex flex-wrap justify-center gap-2 mb-10">
                    {pills.map((pill) => (
                        <span
                            key={pill.label}
                            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 text-sm text-muted-foreground backdrop-blur-sm"
                        >
                            {pill.icon}
                            {pill.label}
                        </span>
                    ))}
                </div>

                {/* Animated waveform */}
                <AnimatedWaveform />

                {/* CTA */}
                <Button
                    asChild
                    size="lg"
                    className="h-12 px-8 rounded-full bg-foreground text-background hover:bg-foreground/90 font-semibold text-sm transition-all hover:scale-105 shadow-lg"
                >
                    <Link href="/chat">
                        Try Awaqi
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                </Button>
            </div>
        </section>
    );
}
