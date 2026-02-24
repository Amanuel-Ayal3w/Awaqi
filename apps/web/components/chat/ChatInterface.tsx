'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Message, Attachment } from './types';
import { chatApi } from '@/lib/api';

const SESSION_STORAGE_KEY = 'awaqi_session_id';

function getOrCreateSessionId(): string {
    if (typeof window === 'undefined') return crypto.randomUUID();
    let id = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!id) {
        id = crypto.randomUUID();
        sessionStorage.setItem(SESSION_STORAGE_KEY, id);
    }
    return id;
}

export function ChatInterface() {
    const t = useTranslations('chat');
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const sessionIdRef = useRef<string>('');

    // Initialise session and load history on mount
    useEffect(() => {
        sessionIdRef.current = getOrCreateSessionId();

        chatApi.getHistory(sessionIdRef.current).then((history) => {
            if (history.length > 0) {
                setMessages(
                    history.map((msg, i) => ({
                        id: `history-${i}`,
                        role: msg.role as 'user' | 'assistant',
                        content: msg.content,
                    }))
                );
            }
        }).catch(() => {
            // History fetch failing is non-fatal (new session)
        });
    }, []);

    const handleSendMessage = async (content: string, attachments: Attachment[]) => {
        if (!content.trim() && attachments.length === 0) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content,
            attachments,
        };
        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);

        try {
            const response = await chatApi.send({
                message: content,
                session_id: sessionIdRef.current,
                language: document.documentElement.lang ?? 'en',
            });

            const botMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.response_text,
            };
            setMessages((prev) => [...prev, botMessage]);
        } catch {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: t('errorMessage'),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full w-full bg-background/50">
            <div className="flex-1 w-full max-w-3xl mx-auto flex flex-col h-full overflow-hidden">
                <MessageList messages={messages} isLoading={isLoading} />
                <div className="p-4 pb-6 w-full">
                    <ChatInput onSend={handleSendMessage} disabled={isLoading} />
                </div>
            </div>
        </div>
    );
}
