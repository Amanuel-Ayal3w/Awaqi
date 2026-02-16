'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export function CTA() {
    const t = useTranslations('landing');

    return (
        <section className="py-24 relative overflow-hidden">
            <div className="container relative z-10">
                <div className="max-w-4xl mx-auto text-center bg-primary text-primary-foreground rounded-3xl p-12 md:p-16 shadow-2xl relative overflow-hidden">
                    {/* Background Pattern */}
                    <div className="absolute top-0 right-0 -m-16 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
                    <div className="absolute bottom-0 left-0 -m-16 w-64 h-64 bg-white/10 rounded-full blur-3xl" />

                    <h2 className="text-3xl md:text-5xl font-bold mb-6 tracking-tight relative z-10">
                        {t('ctaTitle')}
                    </h2>
                    <p className="text-primary-foreground/80 text-lg md:text-xl max-w-2xl mx-auto mb-10 relative z-10">
                        {t('ctaSubtitle')}
                    </p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4 relative z-10">
                        <Button asChild size="lg" variant="secondary" className="h-12 px-8 text-md font-semibold shadow-lg hover:scale-105 transition-transform">
                            <Link href="/login">
                                {t('getStartedFree')}
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                        <Button asChild size="lg" variant="outline" className="h-12 px-8 text-md bg-transparent border-primary-foreground/30 text-primary-foreground hover:bg-primary-foreground/10 hover:text-white">
                            <Link href="/contact">
                                {t('contactSales')}
                            </Link>
                        </Button>
                    </div>
                </div>
            </div>
        </section>
    );
}
