import type { Metadata } from 'next';
import { Inter, Noto_Sans_Ethiopic } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { ClientLayout } from '@/components/layout/ClientLayout';
import { ThemeProvider } from '@/contexts/ThemeContext';
import '../globals.css';

const inter = Inter({
    subsets: ['latin'],
    variable: '--font-inter',
    display: 'swap',
});

const notoSansEthiopic = Noto_Sans_Ethiopic({
    subsets: ['ethiopic'],
    variable: '--font-noto-sans-ethiopic',
    display: 'swap',
});

export const metadata: Metadata = {
    title: 'Revenue Support Bot',
    description: 'Ethiopian Revenue Authority Support Bot - Multilingual Tax Information Assistant',
};

export default async function LocaleLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ locale: string }>;
}) {
    // Await params for Next.js 15 compatibility
    const { locale } = await params;

    // Providing all messages to the client
    // side is the easiest way to get started
    const messages = await getMessages();

    return (
        <html lang={locale} dir="ltr" suppressHydrationWarning>
            <body className={`${inter.variable} ${notoSansEthiopic.variable} font-sans antialiased`}>
                <ThemeProvider>
                    <NextIntlClientProvider messages={messages}>
                        {children}
                    </NextIntlClientProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}


