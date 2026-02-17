'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ArrowRight, CheckCircle2 } from 'lucide-react';

interface FeatureSectionProps {
    title: string;
    description: string;
    features?: string[];
}

const FeatureSection = ({ title, description, features }: FeatureSectionProps) => {
    return (
        <div className="flex flex-col items-center text-center px-4">
            <h3 className="text-2xl font-bold tracking-tight mb-4">{title}</h3>
            <p className="text-muted-foreground mb-8 leading-relaxed text-sm">
                {description}
            </p>

            {features && (
                <div className="flex flex-wrap justify-center gap-2">
                    {features.map((feature, i) => (
                        <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-primary/10 bg-primary/5 text-xs font-medium text-foreground">
                            <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                            <span>{feature}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export function FeatureShowcase() {
    const t = useTranslations('landing');

    return (
        <section className="py-24 bg-background border-t border-border/40">
            <div className="container">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
                    <FeatureSection
                        title={t('step1Title')}
                        description={t('step1Desc')}
                        features={[
                            "Natural language processing",
                            "Context-aware responses",
                            "History tracking"
                        ]}
                    />

                    {/* Vertical dividers for md screens */}
                    <div className="hidden md:block absolute top-1/2 left-1/3 w-px h-24 bg-border/50 -translate-y-1/2" />
                    <div className="hidden md:block absolute top-1/2 right-1/3 w-px h-24 bg-border/50 -translate-y-1/2" />

                    <FeatureSection
                        title={t('step2Title')}
                        description={t('step2Desc')}
                        features={[
                            "Real-time processing",
                            "Accuracy verification",
                            "Legal citation referencing"
                        ]}
                    />

                    <FeatureSection
                        title={t('step3Title')}
                        description={t('step3Desc')}
                        features={[
                            "Clear explanations",
                            "Actionable insights",
                            "Downloadable reports"
                        ]}
                    />
                </div>
            </div>
        </section>
    );
}
