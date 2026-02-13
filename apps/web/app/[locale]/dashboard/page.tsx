import { useTranslations } from 'next-intl';
import { ChatInterface } from '@/components/chat/ChatInterface';

export default function DashboardPage() {
    return (
        <div className="flex flex-col h-full bg-background">
            <ChatInterface />
        </div>
    );
}
