'use client';

import { useTranslations } from 'next-intl';
import { Target, Zap, CheckCircle2 } from 'lucide-react';

const steps = [
    {
        number: '01',
        icon: <Target className="h-5 w-5" />,
        titleKey: 'step1Title' as const,
        descKey: 'step1Desc' as const,
    },
    {
        number: '02',
        icon: <Zap className="h-5 w-5" />,
        titleKey: 'step2Title' as const,
        descKey: 'step2Desc' as const,
    },
    {
        number: '03',
        icon: <CheckCircle2 className="h-5 w-5" />,
        titleKey: 'step3Title' as const,
        descKey: 'step3Desc' as const,
    },
];

export function BentoGridDemo() {
    const t = useTranslations('landing');

    return (
        <section id="how-it-works" className="py-28 border-t border-white/[0.06]">
            <div className="container">
                {/* Section header */}
                <div className="text-center max-w-2xl mx-auto mb-20">
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-muted-foreground mb-6">
                        ✦ {t('howItWorksTitle')}
                    </span>
                    <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4 leading-tight">
                        Simple steps to resolve your tax questions
                    </h2>
                    <p className="text-muted-foreground text-lg">
                        {t('howItWorksSubtitle')}
                    </p>
                </div>

                {/* Steps grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {steps.map((step) => (
                        <div
                            key={step.number}
                            className="group relative rounded-2xl border border-white/[0.08] bg-white/[0.02] p-8 hover:border-white/20 hover:bg-white/[0.04] transition-all duration-300"
                        >
                            {/* Large step number */}
                            <div className="text-7xl font-bold text-white/5 absolute top-6 right-8 leading-none select-none group-hover:text-white/10 transition-colors duration-300">
                                {step.number}
                            </div>

                            {/* Icon */}
                            <div className="w-10 h-10 rounded-xl border border-white/10 bg-white/5 flex items-center justify-center text-muted-foreground mb-6 group-hover:border-white/20 group-hover:text-foreground transition-all duration-300">
                                {step.icon}
                            </div>

                            {/* Text */}
                            <h3 className="text-lg font-semibold mb-3">{t(step.titleKey)}</h3>
                            <p className="text-muted-foreground text-sm leading-relaxed">
                                {t(step.descKey)}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}

// Keep legacy exports for compatibility
export const BentoGrid = ({ children }: { className?: string; children?: React.ReactNode }) => (
    <>{children}</>
);
export const BentoGridItem = ({ title, description }: { className?: string; title?: string | React.ReactNode; description?: string | React.ReactNode; header?: React.ReactNode; icon?: React.ReactNode }) => (
    <div>{title}{description}</div>
);
