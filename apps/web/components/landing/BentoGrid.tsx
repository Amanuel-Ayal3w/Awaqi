'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';
import { Bot, Zap, Shield, BarChart3, Globe, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';

export const BentoGrid = ({ className, children }: { className?: string; children?: ReactNode }) => {
    return (
        <div className={cn("grid md:auto-rows-[18rem] grid-cols-1 md:grid-cols-3 gap-4 max-w-7xl mx-auto", className)}>
            {children}
        </div>
    );
};

export const BentoGridItem = ({
    className,
    title,
    description,
    header,
    icon,
}: {
    className?: string;
    title?: string | ReactNode;
    description?: string | ReactNode;
    header?: ReactNode;
    icon?: ReactNode;
}) => {
    return (
        <div
            className={cn(
                "row-span-1 rounded-xl group/bento hover:shadow-xl transition duration-200 shadow-input dark:shadow-none p-4 dark:bg-black dark:border-white/[0.1] bg-white border border-transparent justify-between flex flex-col space-y-4",
                className
            )}
        >
            {header}
            <div className="group-hover/bento:translate-x-2 transition duration-200">
                {icon}
                <div className="font-sans font-bold text-neutral-600 dark:text-neutral-200 mb-2 mt-2">
                    {title}
                </div>
                <div className="font-sans font-normal text-neutral-600 dark:text-neutral-300 text-xs text-muted-foreground">
                    {description}
                </div>
            </div>
        </div>
    );
};

// Graphics for Bento Grid
const SkeletonOne = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-violet-100 dark:from-violet-900/20 dark:to-black to-violet-50 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
            {/* Abstract Neural Nodes */}
            <div className="relative">
                <div className="w-16 h-16 rounded-full border border-violet-500/30 flex items-center justify-center bg-violet-500/10">
                    <div className="w-8 h-8 rounded-full bg-violet-500/40 animate-pulse shadow-[0_0_15px_rgba(139,92,246,0.5)]" />
                </div>
                <div className="absolute top-0 -left-12 w-8 h-8 rounded-full border border-violet-500/20 bg-violet-500/5" />
                <div className="absolute bottom-0 -right-12 w-8 h-8 rounded-full border border-violet-500/20 bg-violet-500/5" />
            </div>
        </div>
    </div>
);

const SkeletonTwo = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-blue-100 dark:from-blue-900/20 dark:to-black to-blue-50 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:rotate-12 transition-transform duration-500">
            <Globe className="h-20 w-20 text-blue-500/30" />
            <div className="absolute inset-0 bg-gradient-to-t from-background/20 to-transparent" />
        </div>
    </div>
);

const SkeletonThree = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-emerald-100 dark:from-emerald-900/20 dark:to-black to-emerald-50 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
            <Shield className="h-20 w-20 text-emerald-500/30" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-emerald-500/30 blur-xl rounded-full" />
        </div>
    </div>
);

const SkeletonFour = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-amber-100 dark:from-amber-900/20 dark:to-black to-amber-50 items-center justify-center relative overflow-hidden flex-col gap-2 p-4">
        <div className="flex items-end gap-1 h-20 w-full justify-center opacity-80 group-hover:opacity-100 transition-opacity">
            <div className="w-4 bg-amber-500/30 h-[40%] rounded-t-sm" />
            <div className="w-4 bg-amber-500/50 h-[70%] rounded-t-sm" />
            <div className="w-4 bg-amber-500/40 h-[50%] rounded-t-sm" />
            <div className="w-4 bg-amber-500/80 h-[90%] rounded-t-sm shadow-[0_0_10px_rgba(245,158,11,0.3)]" />
            <div className="w-4 bg-amber-500/30 h-[30%] rounded-t-sm" />
        </div>
    </div>
);

// Graphics for Bento Grid
const GraphicAI = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-neutral-200 dark:from-neutral-900 dark:to-neutral-800 to-neutral-100 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:scale-105 transition-transform duration-500">
            <Bot className="h-24 w-24 text-neutral-400/40 group-hover:text-primary/40 transition-colors duration-500" />
            <div className="absolute -bottom-2 -right-2 w-20 h-20 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-colors" />
        </div>
    </div>
);

const GraphicMultilingual = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-neutral-200 dark:from-neutral-900 dark:to-neutral-800 to-neutral-100 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:rotate-6 transition-transform duration-500">
            <Globe className="h-20 w-20 text-neutral-400/40 group-hover:text-blue-500/40 transition-colors duration-500" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-serif text-4xl text-neutral-500/20 font-bold">Aa</div>
        </div>
    </div>
);

const GraphicSecure = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-neutral-200 dark:from-neutral-900 dark:to-neutral-800 to-neutral-100 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
            <Shield className="h-20 w-20 text-neutral-400/40 group-hover:text-emerald-500/40 transition-colors duration-500" />
        </div>
    </div>
);

const GraphicRAG = () => (
    <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-neutral-200 dark:from-neutral-900 dark:to-neutral-800 to-neutral-100 items-center justify-center relative overflow-hidden group">
        <div className="absolute inset-0 flex items-center justify-center group-hover:-translate-y-2 transition-transform duration-500">
            <div className="relative">
                <BarChart3 className="h-20 w-20 text-neutral-400/40 group-hover:text-amber-500/40 transition-colors duration-500" />
                <div className="absolute -bottom-2 -right-2 bg-background p-1.5 rounded-full border border-border shadow-sm">
                    <Sparkles className="h-6 w-6 text-amber-500" />
                </div>
            </div>
        </div>
    </div>
);

export function BentoGridDemo() {
    const t = useTranslations('landing');

    const items = [
        {
            title: t('feature1Title'), // "AI Powered"
            description: t('feature1Desc'),
            header: <GraphicAI />,
            icon: <Bot className="h-4 w-4 text-neutral-500" />,
            className: "md:col-span-2",
        },
        {
            title: t('feature2Title'), // "Multilingual"
            description: t('feature2Desc'),
            header: <GraphicMultilingual />,
            icon: <Globe className="h-4 w-4 text-neutral-500" />,
            className: "md:col-span-1",
        },
        {
            title: t('feature3Title'), // "Secure & Private"
            description: t('feature3Desc'),
            header: <GraphicSecure />,
            icon: <Shield className="h-4 w-4 text-neutral-500" />,
            className: "md:col-span-1",
        },
        {
            title: "Real-time Analytics",
            description: "Track your tax compliance status with real-time dashboards.",
            header: <GraphicRAG />,
            icon: <BarChart3 className="h-4 w-4 text-neutral-500" />,
            className: "md:col-span-2",
        },
    ];

    return (
        <section className="py-24 bg-background">
            <div className="container">
                <div className="text-center max-w-3xl mx-auto mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">{t('howItWorksTitle')}</h2>
                    <p className="text-muted-foreground text-lg">{t('howItWorksSubtitle')}</p>
                </div>
                <BentoGrid>
                    {items.map((item, i) => (
                        <BentoGridItem
                            key={i}
                            title={item.title}
                            description={item.description}
                            header={item.header}
                            icon={item.icon}
                            className={item.className}
                        />
                    ))}
                </BentoGrid>
            </div>
        </section>
    );
}
