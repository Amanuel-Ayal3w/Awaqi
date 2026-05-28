'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Plus, Image as ImageIcon, FileText, X, FileUp, Sparkles, Zap, Bot } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useTranslations } from 'next-intl';
import { Attachment } from './types';
import type { AssistantMode } from '@/types/api';
import { cn } from '@/lib/utils';

interface ChatInputProps {
    onSend: (content: string, attachments: Attachment[]) => void;
    disabled?: boolean;
    mode?: AssistantMode;
    onModeChange?: (mode: AssistantMode) => void;
}

export function ChatInput({ onSend, disabled, mode = 'basic', onModeChange }: ChatInputProps) {
    const [input, setInput] = useState('');
    const [attachments, setAttachments] = useState<Attachment[]>([]);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const imageInputRef = useRef<HTMLInputElement>(null);
    const documentInputRef = useRef<HTMLInputElement>(null);
    const t = useTranslations('chat');

    // Handle Auto-resize
    const adjustHeight = () => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto'; // Reset to calculate
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`; // Max 200px
        }
    };

    useEffect(() => {
        adjustHeight();
    }, [input]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleSend = () => {
        if (!input.trim() && attachments.length === 0) return;
        onSend(input, attachments);
        setInput('');
        setAttachments([]);
        if (textareaRef.current) textareaRef.current.style.height = 'auto';
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, type: 'image' | 'file') => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const newAtt: Attachment = {
                id: Date.now().toString(),
                name: file.name,
                type,
                url: URL.createObjectURL(file) // Create temporary URL for preview
            };
            setAttachments(prev => [...prev, newAtt]);
            e.target.value = ''; // Reset input
        }
    };

    const handleGoogleDriveSelect = () => {
        // Keeping this for Google Drive or fallback
        const newAtt: Attachment = {
            id: Date.now().toString(),
            name: 'drive-file.gdoc',
            type: 'file'
        };
        setAttachments([...attachments, newAtt]);
    };

    return (
        <div className="w-full max-w-3xl mx-auto">
            <div className={cn(
                "relative flex flex-col items-center w-full bg-background rounded-2xl border border-border/60 shadow-lg shadow-primary/5 transition-all duration-200",
                "focus-within:shadow-xl focus-within:shadow-primary/10 focus-within:border-primary/20",
                attachments.length > 0 ? "p-3" : "p-2"
            )}>
                {/* Hidden File Inputs */}
                <input
                    type="file"
                    ref={imageInputRef}
                    className="hidden"
                    accept="image/*"
                    onChange={(e) => handleFileSelect(e, 'image')}
                />
                <input
                    type="file"
                    ref={documentInputRef}
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={(e) => handleFileSelect(e, 'file')}
                />

                {/* Attachment Preview Area */}
                {attachments.length > 0 && (
                    <div className="flex gap-2 mb-2 w-full overflow-x-auto pb-2 scrollbar-thin">
                        {attachments.map((att) => (
                            <div key={att.id} className="relative flex items-center gap-2 bg-muted/50 p-2 pl-3 rounded-xl border text-xs group">
                                {att.type === 'image' ? <ImageIcon className="h-3.5 w-3.5 text-muted-foreground" /> : <FileText className="h-3.5 w-3.5 text-muted-foreground" />}
                                <span className="truncate max-w-[120px] font-medium">{att.name}</span>
                                <button
                                    onClick={() => setAttachments(atts => atts.filter(a => a.id !== att.id))}
                                    className="ml-1 p-0.5 rounded-full hover:bg-destructive/10 hover:text-destructive transition-colors opacity-60 group-hover:opacity-100"
                                >
                                    <X className="h-3 w-3" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                <div className="flex items-end w-full gap-2">
                    {/* Mode selector */}
                    {onModeChange && (
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className={cn(
                                        "h-10 shrink-0 rounded-full px-3 text-xs font-medium",
                                        mode === 'awaqi_max'
                                            ? "bg-primary/10 text-primary hover:bg-primary/15"
                                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    )}
                                    disabled={disabled}
                                    aria-label="Assistant mode"
                                >
                                    {mode === 'awaqi_max' ? (
                                        <Zap className="mr-1.5 h-3.5 w-3.5" />
                                    ) : (
                                        <Bot className="mr-1.5 h-3.5 w-3.5" />
                                    )}
                                    <span className="hidden sm:inline">
                                        {mode === 'awaqi_max' ? 'Awaqi Max' : 'Basic'}
                                    </span>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start" className="w-72 p-1 rounded-xl shadow-lg border-border/60">
                                <DropdownMenuItem
                                    onClick={() => onModeChange('basic')}
                                    className="rounded-lg cursor-pointer items-start gap-2 py-2"
                                >
                                    <Bot className="mt-0.5 h-4 w-4" />
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium">Basic</span>
                                        <span className="text-[11px] text-muted-foreground">
                                            Single-pass RAG over the indexed tax KB. Fast and predictable.
                                        </span>
                                    </div>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => onModeChange('awaqi_max')}
                                    className="rounded-lg cursor-pointer items-start gap-2 py-2"
                                >
                                    <Zap className="mt-0.5 h-4 w-4 text-primary" />
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium">Awaqi Max</span>
                                        <span className="text-[11px] text-muted-foreground">
                                            ReAct agent: iterative KB search + Ethiopian-grounded web
                                            search. Higher quality on hard questions, slower.
                                        </span>
                                    </div>
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    )}

                    {/* Attachment Menu */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-10 w-10 shrink-0 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                                disabled={disabled}
                            >
                                <Plus className="h-5 w-5" />
                                <span className="sr-only">{t('addAttachment')}</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start" className="w-56 p-1 rounded-xl shadow-lg border-border/60">
                            <DropdownMenuItem onClick={() => imageInputRef.current?.click()} className="rounded-lg cursor-pointer">
                                <ImageIcon className="mr-2 h-4 w-4" />
                                <span>{t('uploadImage')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => documentInputRef.current?.click()} className="rounded-lg cursor-pointer">
                                <FileUp className="mr-2 h-4 w-4" />
                                <span>{t('uploadDocument')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleGoogleDriveSelect} className="rounded-lg cursor-pointer">
                                <FileText className="mr-2 h-4 w-4" />
                                <span>{t('googleDrive')}</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Textarea */}
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={t('placeholder')}
                        disabled={disabled}
                        className="flex-1 max-h-[200px] min-h-[40px] bg-transparent border-0 focus:ring-0 resize-none py-2.5 px-2 text-sm placeholder:text-muted-foreground/70 focus-visible:outline-none leading-relaxed"
                        rows={1}
                    />

                    {/* Send Button */}
                    <Button
                        onClick={handleSend}
                        disabled={disabled || (!input.trim() && attachments.length === 0)}
                        size="icon"
                        className={cn(
                            "h-10 w-10 shrink-0 rounded-full transition-all duration-200 shadow-sm",
                            input.trim() || attachments.length > 0
                                ? "bg-primary text-primary-foreground hover:opacity-90 hover:scale-105"
                                : "bg-muted text-muted-foreground opacity-50"
                        )}
                    >
                        {input.trim() || attachments.length > 0 ? (
                            <Send className="h-4 w-4" />
                        ) : (
                            <Sparkles className="h-4 w-4" />
                        )}
                        <span className="sr-only">{t('send')}</span>
                    </Button>
                </div>
            </div>
            <div className="text-center mt-3">
                <p className="text-[10px] text-muted-foreground/60">
                    AI-generated responses may be inaccurate. Please verify important tax information.
                </p>
            </div>
        </div>
    );
}
