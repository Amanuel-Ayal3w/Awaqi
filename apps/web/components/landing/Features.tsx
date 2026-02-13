'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Bot, Globe, ShieldCheck } from 'lucide-react';

export function Features() {
    const t = useTranslations('landing');

    const features = [
        {
            icon: <Bot className="h-10 w-10 text-primary" />,
            title: t('feature1Title'),
            description: t('feature1Desc')
        },
        {
            icon: <Globe className="h-10 w-10 text-primary" />,
            title: t('feature2Title'),
            description: t('feature2Desc')
        },
        {
            icon: <ShieldCheck className="h-10 w-10 text-primary" />,
            title: t('feature3Title'),
            description: t('feature3Desc')
        }
    ];

    return (
        <section className="py-24 relative z-10">
            <div className="container">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {features.map((feature, index) => (
                        <Card key={index} className="bg-background/40 backdrop-blur-md border-primary/10 hover:border-primary/30 transition-all hover:-translate-y-1 duration-300">
                            <CardHeader>
                                <div className="mb-4 p-3 bg-muted/50 rounded-2xl w-fit">
                                    {feature.icon}
                                </div>
                                <CardTitle className="text-xl">{feature.title}</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-muted-foreground leading-relaxed">
                                    {feature.description}
                                </p>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        </section>
    );
}
