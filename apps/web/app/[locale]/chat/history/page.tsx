'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { chatApi } from '@/lib/api';
import { getOrCreateSessionId } from '@/lib/chat-session';
import type { ChatMessage } from '@/types/api';

export default function HistoryPage() {
    const t = useTranslations('common');
    const [messages, setMessages] = React.useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = React.useState(true);

    React.useEffect(() => {
        const sessionId = getOrCreateSessionId();

        chatApi
            .getHistory(sessionId)
            .then((history) => {
                setMessages(history);
            })
            .catch(() => {
                setMessages([]);
            })
            .finally(() => {
                setIsLoading(false);
            });
    }, []);

    return (
        <div className="space-y-4">
            <h1 className="text-3xl font-bold">{t('history')}</h1>

            {isLoading && <p className="text-muted-foreground">Loading history...</p>}

            {!isLoading && messages.length === 0 && (
                <p className="text-muted-foreground">No chat history found for this session.</p>
            )}

            {!isLoading && messages.length > 0 && (
                <div className="space-y-2">
                    {messages.map((message, index) => (
                        <div key={`${message.timestamp}-${index}`} className="rounded-lg border p-3">
                            <div className="text-xs text-muted-foreground mb-1">
                                {message.role} • {new Date(message.timestamp).toLocaleString()}
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
