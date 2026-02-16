'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Star } from 'lucide-react';

export function Testimonials() {
    const t = useTranslations('landing');

    const testimonials = [
        {
            name: "Lydia Tadesse",
            role: "Financial Consultant",
            content: "Using the Ethio Revenue Bot has saved me hours of research time. The answers are accurate and the references to the tax proclamations are invaluable.",
            initials: "LT"
        },
        {
            name: "Kebede Michael",
            role: "Small Business Owner",
            content: "Finally, a way to understand my tax obligations without hiring expensive consultants. The step-by-step guidance is perfect for beginners.",
            initials: "KM"
        },
        {
            name: "Sara Abraham",
            role: "Accountant",
            content: "I recommend this tool to all my clients. It's the most up-to-date resource for Ethiopian tax laws available online.",
            initials: "SA"
        }
    ];

    return (
        <section className="py-24">
            <div className="container">
                <div className="text-center max-w-2xl mx-auto mb-16">
                    <h2 className="text-3xl font-bold tracking-tight mb-4">{t('testimonialsTitle')}</h2>
                    <p className="text-muted-foreground text-lg">{t('testimonialsSubtitle')}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {testimonials.map((item, index) => (
                        <Card key={index} className="border bg-card/50 backdrop-blur-sm">
                            <CardHeader className="flex flex-row items-center gap-4 pb-2">
                                <Avatar className="h-12 w-12 border-2 border-primary/10">
                                    <AvatarFallback className="bg-primary/5 text-primary font-medium">{item.initials}</AvatarFallback>
                                </Avatar> // Mock avatars are fine
                                <div>
                                    <p className="font-semibold text-sm">{item.name}</p>
                                    <p className="text-xs text-muted-foreground">{item.role}</p>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="flex gap-0.5 mb-3 text-amber-500">
                                    {[...Array(5)].map((_, i) => (
                                        <Star key={i} className="h-4 w-4 fill-current" />
                                    ))}
                                </div>
                                <p className="text-muted-foreground text-sm italic">"{item.content}"</p>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        </section>
    );
}
