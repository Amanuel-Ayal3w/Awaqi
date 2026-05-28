'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Message, Attachment } from './types';
import type { AssistantMode } from '@/types/api';
import { chatApi } from '@/lib/api';
import { customerAuthClient } from '@/lib/customer-auth-client';
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
    const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);
    const [migrated, setMigrated] = useState(false);
    const [mode, setMode] = useState<AssistantMode>(() => {
        if (typeof window === 'undefined') return 'basic';
        const saved = window.localStorage.getItem('awaqi:assistantMode');
        return saved === 'awaqi_max' ? 'awaqi_max' : 'basic';
    });

    const handleModeChange = useCallback((next: AssistantMode) => {
        setMode(next);
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('awaqi:assistantMode', next);
        }
    }, []);
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
                        citations:
                            msg.citations && msg.citations.length > 0
                                ? msg.citations
                                : undefined,
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

    // Check auth state once on mount so we can show/hide the login-to-save banner
    useEffect(() => {
        customerAuthClient.getSession().then(({ data }) => {
            setIsLoggedIn(!!data?.session);
        }).catch(() => setIsLoggedIn(false));
    }, []);

    const handleSendMessage = async (content: string, attachments: Attachment[] = []) => {
        if (!content.trim() && attachments.length === 0) return;

        // Strip follow-up chips from the previous last assistant message when a new message is sent
        setMessages((prev) =>
            prev.map((m, i) =>
                i === prev.length - 1 && m.role === 'assistant'
                    ? { ...m, followUpSuggestions: undefined }
                    : m
            )
        );

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
                mode,
            }, token);

            if (response.session_token) {
                setSessionToken(sessionIdRef.current, response.session_token);
            }

            const botMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.response_text,
                citations:
                    response.citations && response.citations.length > 0
                        ? response.citations
                        : undefined,
                followUpSuggestions:
                    response.follow_up_suggestions && response.follow_up_suggestions.length > 0
                        ? response.follow_up_suggestions
                        : undefined,
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

    const handleFollowUpClick = (text: string) => {
        handleSendMessage(text);
    };

    const handleSaveChat = async () => {
        try {
            // Open the login page; after auth the user returns and migration can be triggered
            const locale = document.documentElement.lang ?? 'en';
            const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = `/${locale}/chat/login?redirect=${returnUrl}&migrate_session=${sessionIdRef.current}`;
        } catch {
            // ignore
        }
    };

    const handleExportTranscript = async () => {
        if (messages.length === 0) return;
        try {
            const token = getSessionToken(sessionIdRef.current);
            const text = await chatApi.exportTranscript(sessionIdRef.current, token);
            const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `awaqi-chat-${sessionIdRef.current}.txt`;
            a.rel = 'noopener';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch {
            // keep UX quiet; user can retry
        }
    };

    const showSaveBanner =
        isLoggedIn === false && !migrated && messages.some((m) => m.role === 'user');

    return (
        <div className="flex flex-col h-full w-full bg-background/50">
            <div className="flex-1 w-full max-w-3xl mx-auto flex flex-col h-full overflow-hidden">
                {/* Login-to-save banner (AWA-34) */}
                {showSaveBanner && (
                    <div className="mx-4 mt-3 flex items-center justify-between gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 text-sm animate-in fade-in duration-300">
                        <span className="text-muted-foreground">{t('savePrompt', { defaultMessage: 'Login to save this conversation' })}</span>
                        <button
                            onClick={handleSaveChat}
                            className="shrink-0 rounded-lg bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                            {t('loginToSave', { defaultMessage: 'Login' })}
                        </button>
                    </div>
                )}
                <MessageList
                    messages={messages}
                    isLoading={isLoading}
                    onExportTranscript={handleExportTranscript}
                    onFollowUpClick={handleFollowUpClick}
                />
                <div className="p-4 pb-6 w-full">
                    <ChatInput
                        onSend={handleSendMessage}
                        disabled={isLoading}
                        mode={mode}
                        onModeChange={handleModeChange}
                    />
                </div>
            </div>
        </div>
    );
}
