'use client';

import React, { useEffect, useRef } from 'react';
import { Message } from './types';
import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';
import { Paperclip, Sparkles, User, Bot } from 'lucide-react';

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
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground animate-in fade-in duration-500">
                <div className="bg-primary/5 p-4 rounded-full mb-4">
                    <Sparkles className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold mb-2 text-foreground tracking-tight">Revenue Support Bot</h2>
                <p className="max-w-sm text-sm">{t('placeholder')}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth" ref={scrollRef}>
            {messages.map((msg) => (
                <div
                    key={msg.id}
                    className={cn(
                        "flex w-full gap-3",
                        msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                >
                    <div
                        className={cn(
                            "max-w-[80%] rounded-2xl px-5 py-3.5 text-sm shadow-sm",
                            msg.role === 'user'
                                ? "bg-primary text-primary-foreground rounded-br-sm"
                                : "bg-card border border-border/50 text-foreground rounded-bl-sm"
                        )}
                    >
                        {msg.attachments && msg.attachments.length > 0 && (
                            <div className="mb-3 space-y-2">
                                {msg.attachments.map(att => (
                                    <div key={att.id} className="flex items-center gap-2 text-xs bg-background/20 p-2 rounded-md border border-white/10">
                                        <Paperclip className="w-3.5 h-3.5" />
                                        <span className="truncate">{att.name}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                        <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                    </div>
                </div>
            ))}
            {isLoading && (
                <div className="flex justify-start gap-3">
                    <div className="bg-card border border-border/50 text-foreground rounded-2xl rounded-bl-sm px-5 py-3.5 text-sm shadow-sm flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
                        <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
                        <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce" />
                    </div>
                </div>
            )}
        </div>
    );
}
