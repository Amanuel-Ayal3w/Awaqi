'use client';

import { Suspense } from 'react';
import { ChatInterface } from '@/components/chat/ChatInterface';

export default function DashboardPage() {
    return (
        <div className="flex flex-col h-full bg-background">
            <Suspense>
                <ChatInterface />
            </Suspense>
        </div>
    );
}
