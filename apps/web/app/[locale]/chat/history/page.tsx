import { useTranslations } from 'next-intl';

export default function HistoryPage() {
    const t = useTranslations('common');

    return (
        <div className="space-y-4">
            <h1 className="text-3xl font-bold">{t('history')}</h1>
            <p className="text-muted-foreground">
                Chat history will be displayed here.
            </p>
        </div>
    );
}
