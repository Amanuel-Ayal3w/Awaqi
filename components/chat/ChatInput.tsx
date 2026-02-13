'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Plus, Image as ImageIcon, FileText, X, FileUp } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useTranslations } from 'next-intl';
import { Attachment } from './types';
import { cn } from '@/lib/utils';

interface ChatInputProps {
    onSend: (content: string, attachments: Attachment[]) => void;
    disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
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
        <div className="relative flex flex-col items-center w-full bg-muted/50 rounded-2xl border focus-within:ring-1 focus-within:ring-ring transition-all">
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
                <div className="flex gap-2 p-2 w-full overflow-x-auto">
                    {attachments.map((att) => (
                        <div key={att.id} className="relative flex items-center gap-2 bg-background p-2 rounded-md border text-xs">
                            {att.type === 'image' ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                            <span className="truncate max-w-[100px]">{att.name}</span>
                            <button
                                onClick={() => setAttachments(atts => atts.filter(a => a.id !== att.id))}
                                className="ml-1 hover:text-destructive"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            <div className="flex items-end w-full p-2 gap-2">
                {/* Attachment Menu */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-9 w-9 shrink-0 rounded-full hover:bg-muted-foreground/10 text-muted-foreground"
                            disabled={disabled}
                        >
                            <Plus className="h-5 w-5" />
                            <span className="sr-only">{t('addAttachment')}</span>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-56">
                        <DropdownMenuItem onClick={() => imageInputRef.current?.click()}>
                            <ImageIcon className="mr-2 h-4 w-4" />
                            <span>{t('uploadImage')}</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => documentInputRef.current?.click()}>
                            <FileUp className="mr-2 h-4 w-4" />
                            <span>{t('uploadDocument')}</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={handleGoogleDriveSelect}>
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
                    className="flex-1 max-h-[200px] min-h-[24px] bg-transparent border-0 focus:ring-0 resize-none py-2 px-0 text-sm placeholder:text-muted-foreground focus-visible:outline-none"
                    rows={1}
                />

                {/* Send Button */}
                <Button
                    onClick={handleSend}
                    disabled={disabled || (!input.trim() && attachments.length === 0)}
                    size="icon"
                    className={cn(
                        "h-9 w-9 shrink-0 rounded-full transition-all",
                        input.trim() || attachments.length > 0 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                    )}
                >
                    <Send className="h-4 w-4" />
                    <span className="sr-only">{t('send')}</span>
                </Button>
            </div>
        </div>
    );
}
