'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Message, Attachment } from './types';
import { chatApi } from '@/lib/api';
import {
    createNewSession,
    getOrCreateSessionId,
    getSessionToken,
    setActiveSession,
    setSessionToken,
    updateSessionTitle,
} from '@/lib/chat-session';

export function ChatInterface() {
    const t = useTranslations('chat');
    const searchParams = useSearchParams();
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const sessionIdRef = useRef<string>('');
    const hasSavedTitleRef = useRef(false);

    const sessionParam = searchParams.get('session');

    const initSession = useCallback(() => {
        if (sessionParam) {
            sessionIdRef.current = sessionParam;
            setActiveSession(sessionParam);
        } else {
            sessionIdRef.current = getOrCreateSessionId();
        }
        hasSavedTitleRef.current = false;

        const token = getSessionToken(sessionIdRef.current);
        chatApi.getHistory(sessionIdRef.current, token).then((history) => {
            if (history.length > 0) {
                setMessages(
                    history.map((msg, i) => ({
                        id: `history-${i}`,
                        role: msg.role as 'user' | 'assistant',
                        content: msg.content,
                    }))
                );
                hasSavedTitleRef.current = true;
            } else {
                setMessages([]);
            }
        }).catch(() => {
            setMessages([]);
        });
    }, [sessionParam]);

    useEffect(() => {
        initSession();
    }, [initSession]);

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

        if (!hasSavedTitleRef.current) {
            const baseTitle = content.trim() || attachments[0]?.name || 'New chat';
            const title = baseTitle.length > 60 ? baseTitle.slice(0, 57) + '...' : baseTitle;
            updateSessionTitle(sessionIdRef.current, title);
            hasSavedTitleRef.current = true;
        }

        try {
            const token = getSessionToken(sessionIdRef.current);
            const response = await chatApi.send({
                message: content,
                session_id: sessionIdRef.current,
                language: document.documentElement.lang ?? 'en',
            }, token);

            if (response.session_token) {
                setSessionToken(sessionIdRef.current, response.session_token);
            }

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
                content: t('error'),
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
