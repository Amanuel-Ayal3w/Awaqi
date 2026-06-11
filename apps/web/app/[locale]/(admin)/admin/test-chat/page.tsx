'use client';

import { Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { Button } from '@/components/ui/button';

export default function AdminTestChatPage() {
    const router = useRouter();
    const locale = useLocale();

    const newTestSession = () => {
        router.replace(`/${locale}/admin/test-chat?session=${crypto.randomUUID()}`);
    };

    return (
        <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-start justify-between gap-3 rounded-lg border bg-card p-4 text-sm">
                <Button type="button" variant="secondary" size="sm" onClick={newTestSession}>
                    New test session
                </Button>
            </div>
            <div className="flex h-[calc(100vh-10rem)] min-h-[400px] max-h-[56rem] flex-col overflow-hidden rounded-lg border bg-background shadow-sm">
                <Suspense
                    fallback={
                        <div className="flex flex-1 items-center justify-center p-6 text-muted-foreground">
                            Loading chat…
                        </div>
                    }
                >
                    <div className="flex min-h-0 flex-1 flex-col">
                        <ChatInterface />
                    </div>
                </Suspense>
            </div>
        </div>
    );
}
