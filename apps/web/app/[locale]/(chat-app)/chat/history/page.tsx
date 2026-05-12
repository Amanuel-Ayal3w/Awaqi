import { redirect } from 'next/navigation';

export default async function HistoryPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    redirect(`/${locale}/chat`);
}
