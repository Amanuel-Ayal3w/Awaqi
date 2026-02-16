'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

import { Message, Attachment } from './types';

export function ChatInterface() {
    const t = useTranslations('chat');
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const handleSendMessage = async (content: string, attachments: Attachment[]) => {
        if (!content.trim() && attachments.length === 0) return;

        // Add User Message
        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content,
            attachments
        };
        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);

        // Simulate Bot Response (Mock)
        setTimeout(() => {
            const botMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "Base Chat Implementation. Backend integration pending."
            };
            setMessages(prev => [...prev, botMessage]);
            setIsLoading(false);
        }, 1000);
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
