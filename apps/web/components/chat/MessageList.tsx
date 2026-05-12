'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { Citation } from '@/types/api';
import { Message } from './types';
import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';
import { ChevronDown, ChevronUp, Paperclip, Sparkles } from 'lucide-react';

function citationPillTitle(c: Citation, index: number): string {
    const raw = c.document_title?.trim() || c.source?.trim() || '';
    const base = raw || `Source ${index + 1}`;
    return base.length > 52 ? `${base.slice(0, 49)}…` : base;
}

interface MessageListProps {
    messages: Message[];
    isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const t = useTranslations('chat');
    const [openCitationKey, setOpenCitationKey] = useState<string | null>(null);

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
                <h2 className="text-xl font-semibold mb-2 text-foreground tracking-tight">Awaqi</h2>
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
                        'flex w-full gap-3',
                        msg.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                >
                    <div
                        className={cn(
                            'max-w-[80%] rounded-2xl px-5 py-3.5 text-sm shadow-sm',
                            msg.role === 'user'
                                ? 'bg-primary text-primary-foreground rounded-br-sm'
                                : 'bg-card border border-border/50 text-foreground rounded-bl-sm'
                        )}
                    >
                        {msg.attachments && msg.attachments.length > 0 && (
                            <div className="mb-3 space-y-2">
                                {msg.attachments.map((att) => (
                                    <div
                                        key={att.id}
                                        className="flex items-center gap-2 text-xs bg-background/20 p-2 rounded-md border border-white/10"
                                    >
                                        <Paperclip className="w-3.5 h-3.5" />
                                        <span className="truncate">{att.name}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                        <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                        {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 ? (
                            <div className="mt-3 pt-3 border-t border-border/60">
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                                    {t('sources')}
                                </p>
                                <div className="flex flex-col gap-2">
                                    {msg.citations.map((c, i) => {
                                        const key = `${msg.id}:${i}`;
                                        const open = openCitationKey === key;
                                        return (
                                            <div key={key}>
                                                <button
                                                    type="button"
                                                    onClick={() => setOpenCitationKey(open ? null : key)}
                                                    className="inline-flex w-full max-w-full items-center justify-between gap-2 rounded-full border border-border/60 bg-muted/70 px-3 py-1.5 text-left text-xs text-foreground hover:bg-muted"
                                                >
                                                    <span className="min-w-0 truncate font-medium">
                                                        {citationPillTitle(c, i)}
                                                    </span>
                                                    {open ? (
                                                        <ChevronUp className="h-3.5 w-3.5 shrink-0 opacity-70" />
                                                    ) : (
                                                        <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-70" />
                                                    )}
                                                </button>
                                                {open ? (
                                                    <div className="mt-2 space-y-2 rounded-lg border border-border/40 bg-muted/30 p-3 text-xs leading-relaxed">
                                                        {(c.proclamation_number || c.article_number) && (
                                                            <p className="text-muted-foreground">
                                                                {c.proclamation_number ? (
                                                                    <span>Proc. {c.proclamation_number}</span>
                                                                ) : null}
                                                                {c.proclamation_number && c.article_number ? (
                                                                    <span> · </span>
                                                                ) : null}
                                                                {c.article_number ? (
                                                                    <span>Art. {c.article_number}</span>
                                                                ) : null}
                                                            </p>
                                                        )}
                                                        <p className="text-muted-foreground">Page {c.page}</p>
                                                        <p className="whitespace-pre-wrap text-foreground">
                                                            {c.text}
                                                        </p>
                                                    </div>
                                                ) : null}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ) : null}
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
