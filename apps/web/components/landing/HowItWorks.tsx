'use client';

import { useTranslations } from 'next-intl';
import { Target, Zap, CheckCircle2 } from 'lucide-react';

export function HowItWorks() {
    const t = useTranslations('landing');

    const steps = [
        {
            icon: <Target className="h-6 w-6 text-primary" />,
            title: t('step1Title'),
            description: t('step1Desc')
        },
        {
            icon: <Zap className="h-6 w-6 text-primary" />,
            title: t('step2Title'),
            description: t('step2Desc')
        },
        {
            icon: <CheckCircle2 className="h-6 w-6 text-primary" />,
            title: t('step3Title'),
            description: t('step3Desc')
        }
    ];

    return (
        <section className="py-24 bg-muted/30">
            <div className="container">
                <div className="text-center max-w-3xl mx-auto mb-16">
                    <h2 className="text-3xl font-bold tracking-tight mb-4">{t('howItWorksTitle')}</h2>
                    <p className="text-muted-foreground text-lg">{t('howItWorksSubtitle')}</p>
                </div>

                <div className="relative grid grid-cols-1 md:grid-cols-3 gap-12">
                    {/* Connecting Line (Desktop) */}
                    <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-primary/20 -z-10" />

                    {steps.map((step, index) => (
                        <div key={index} className="flex flex-col items-center text-center group">
                            <div className="w-24 h-24 rounded-full bg-background border-4 border-muted flex items-center justify-center mb-6 shadow-sm group-hover:border-primary/50 transition-colors duration-300">
                                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                                    {step.icon}
                                </div>
                            </div>
                            <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                            <p className="text-muted-foreground leading-relaxed max-w-xs">{step.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
