'use client';

import React, { useEffect, useRef } from 'react';
import { Message } from './types';
import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';

interface MessageListProps {
    messages: Message[];
    isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const t = useTranslations('chat');

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
                <h2 className="text-2xl font-bold mb-2">Revenue Support Bot</h2>
                <p>{t('placeholder')}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
            {messages.map((msg) => (
                <div
                    key={msg.id}
                    className={cn(
                        "flex w-full",
                        msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                >
                    <div
                        className={cn(
                            "max-w-[80%] rounded-lg px-4 py-3 text-sm",
                            msg.role === 'user'
                                ? "bg-primary text-primary-foreground rounded-br-none"
                                : "bg-muted text-foreground rounded-bl-none"
                        )}
                    >
                        {msg.attachments && msg.attachments.length > 0 && (
                            <div className="mb-2 space-y-2">
                                {msg.attachments.map(att => (
                                    <div key={att.id} className="text-xs bg-background/20 p-1 rounded">
                                        📎 {att.name}
                                    </div>
                                ))}
                            </div>
                        )}
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                </div>
            ))}
            {isLoading && (
                <div className="flex justify-start">
                    <div className="bg-muted text-foreground rounded-lg rounded-bl-none px-4 py-3 text-sm animate-pulse">
                        {t('thinking')}
                    </div>
                </div>
            )}
        </div>
    );
}
