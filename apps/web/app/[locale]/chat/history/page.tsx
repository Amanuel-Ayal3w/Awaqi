import { redirect } from 'next/navigation';

export default function HistoryPage({ params }: { params: { locale: string } }) {
    redirect(`/${params.locale}/chat`);
}
