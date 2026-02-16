'use client';

import { useTranslations } from 'next-intl';

export function Logos() {
    const t = useTranslations('landing');

    // Placeholder logos - in a real app these would be SVGs
    const partners = [
        "Ministry of Revenue",
        "Ethiopian Airlines",
        "Ethio Telecom",
        "Commercial Bank of Ethiopia",
        "Addis Ababa University"
    ];

    return (
        <section className="py-12 border-y border-border/40 bg-background/50 backdrop-blur-sm">
            <div className="container">
                <p className="text-center text-sm font-medium text-muted-foreground mb-8">
                    {t('trustedBy')}
                </p>
                <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-70 grayscale hover:grayscale-0 transition-all duration-500">
                    {partners.map((partner, index) => (
                        <div key={index} className="text-lg font-bold text-muted-foreground hover:text-foreground transition-colors cursor-default">
                            {partner}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
