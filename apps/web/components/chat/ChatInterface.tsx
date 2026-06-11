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

    const abortRef = useRef<(() => void) | null>(null);

    const handleSendMessage = async (content: string, attachments: Attachment[] = []) => {
        if (!content.trim() && attachments.length === 0) return;

        // Cancel any in-flight stream
        abortRef.current?.();
        abortRef.current = null;

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

        const botId = (Date.now() + 1).toString();

        // Optimistically add an empty assistant message that will be filled in
        setMessages((prev) => [
            ...prev,
            { id: botId, role: 'assistant', content: '', isStreaming: true } as Message,
        ]);

        const token = getSessionToken(sessionIdRef.current);

        const abort = chatApi.sendStream(
            {
                message: content,
                session_id: sessionIdRef.current,
                language: document.documentElement.lang ?? 'en',
                mode,
            },
            token,
            (event) => {
                if (event.type === 'delta') {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === botId
                                ? { ...m, content: m.content + event.text }
                                : m
                        )
                    );
                } else if (event.type === 'status') {
                    // Show tool-call progress as italic placeholder while content is still empty
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === botId && m.content === ''
                                ? { ...m, statusText: event.text }
                                : m
                        )
                    );
                } else if (event.type === 'done') {
                    if (event.session_token) {
                        setSessionToken(sessionIdRef.current, event.session_token);
                    }
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === botId
                                ? {
                                      ...m,
                                      content: event.response_text,
                                      isStreaming: false,
                                      statusText: undefined,
                                      citations:
                                          event.citations && event.citations.length > 0
                                              ? event.citations
                                              : undefined,
                                      followUpSuggestions:
                                          event.follow_up_suggestions &&
                                          event.follow_up_suggestions.length > 0
                                              ? event.follow_up_suggestions
                                              : undefined,
                                      confidenceScore:
                                          typeof event.confidence_score === 'number'
                                              ? event.confidence_score
                                              : undefined,
                                  }
                                : m
                        )
                    );
                    setIsLoading(false);
                    abortRef.current = null;
                } else if (event.type === 'error') {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === botId
                                ? { ...m, content: t('error'), isStreaming: false, statusText: undefined }
                                : m
                        )
                    );
                    setIsLoading(false);
                    abortRef.current = null;
                }
            },
            () => {
                // network / fetch error
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === botId
                            ? { ...m, content: t('error'), isStreaming: false, statusText: undefined }
                            : m
                    )
                );
                setIsLoading(false);
                abortRef.current = null;
            },
        );

        abortRef.current = abort;
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
