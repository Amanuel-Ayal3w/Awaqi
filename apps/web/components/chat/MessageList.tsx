'use client';

import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Citation } from '@/types/api';
import { Message } from './types';
import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';
import {
    BookOpen,
    ChevronDown,
    ChevronRight,
    ChevronUp,
    Copy,
    Download,
    ExternalLink,
    Paperclip,
    Sparkles,
    ThumbsDown,
    ThumbsUp,
    X,
    Gauge,
} from 'lucide-react';

function citationPillTitle(c: Citation, index: number): string {
    const raw = c.document_title?.trim() || c.source?.trim() || '';
    const base = raw || `Source ${index + 1}`;
    return base.length > 52 ? `${base.slice(0, 49)}…` : base;
}

function EnforcementBadge({ status }: { status?: string }) {
    const isDraft = status === 'draft';
    return (
        <span
            className={cn(
                'inline-flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0',
                isDraft
                    ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                    : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            )}
        >
            {isDraft ? 'Draft' : 'In Effect'}
        </span>
    );
}

function ConfidencePill({ score }: { score: number }) {
    const pct = Math.round(score * 100);
    const tier =
        pct >= 75
            ? { label: 'High', classes: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' }
            : pct >= 50
            ? { label: 'Med', classes: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' }
            : { label: 'Low', classes: 'bg-rose-500/10 text-rose-600 dark:text-rose-400' };

    return (
        <span
            title={`Confidence: ${pct}%`}
            className={cn(
                'flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium select-none cursor-default',
                tier.classes
            )}
        >
            <Gauge className="w-3 h-3" />
            {pct}%
        </span>
    );
}

/* ── Sources Sidebar ──────────────────────────────────────────────────────── */

interface SourcesSidebarProps {
    citations: Citation[];
    onClose: () => void;
}

function SourcesSidebar({ citations, onClose }: SourcesSidebarProps) {
    const [expanded, setExpanded] = useState<number | null>(null);

    return (
        <>
            {/* Backdrop (mobile) */}
            <div
                className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px] md:hidden"
                onClick={onClose}
            />

            {/* Panel */}
            <div className="fixed right-0 top-0 h-full w-full max-w-sm bg-card border-l border-border/60 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3.5 border-b border-border/50 bg-card/80 backdrop-blur shrink-0">
                    <div className="flex items-center gap-2">
                        <BookOpen className="w-4 h-4 text-primary" />
                        <span className="font-semibold text-sm">Sources</span>
                        <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5 font-medium">
                            {citations.length}
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-colors"
                        aria-label="Close sources panel"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Citation list */}
                <div className="flex-1 overflow-y-auto p-3 space-y-2 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                    {citations.map((c, i) => {
                        const isExpanded = expanded === i;
                        const title =
                            c.document_title?.trim() ||
                            c.source?.trim() ||
                            `Source ${i + 1}`;

                        return (
                            <div
                                key={i}
                                className="rounded-xl border border-border/50 bg-background overflow-hidden"
                            >
                                <button
                                    type="button"
                                    onClick={() =>
                                        setExpanded(isExpanded ? null : i)
                                    }
                                    className="w-full px-3 py-3 text-left flex items-start gap-2.5 hover:bg-muted/30 transition-colors"
                                >
                                    {/* Index badge */}
                                    <span className="mt-0.5 shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center">
                                        {i + 1}
                                    </span>

                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-semibold text-foreground leading-snug line-clamp-2">
                                            {title}
                                        </p>
                                        <div className="flex items-center flex-wrap gap-1.5 mt-1.5">
                                            <EnforcementBadge
                                                status={c.enforcement_status}
                                            />
                                            {c.page && (
                                                <span className="text-[10px] text-muted-foreground">
                                                    p.&nbsp;{c.page}
                                                </span>
                                            )}
                                            {c.proclamation_number && (
                                                <span className="text-[10px] text-muted-foreground">
                                                    Proc.&nbsp;
                                                    {c.proclamation_number}
                                                </span>
                                            )}
                                            {c.article_number && (
                                                <span className="text-[10px] text-muted-foreground">
                                                    Art.&nbsp;{c.article_number}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {isExpanded ? (
                                        <ChevronUp className="w-3.5 h-3.5 shrink-0 text-muted-foreground mt-1" />
                                    ) : (
                                        <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground mt-1" />
                                    )}
                                </button>

                                {isExpanded && (
                                    <div className="px-3 pb-3 pt-1 border-t border-border/30 space-y-2">
                                        <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
                                            {c.text}
                                        </p>
                                        {c.source_url && (
                                            <a
                                                href={c.source_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center gap-1 text-[11px] text-primary hover:opacity-80 transition-opacity font-medium"
                                            >
                                                <ExternalLink className="w-3 h-3" />
                                                Open document
                                            </a>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </>
    );
}

/* ── MessageList ──────────────────────────────────────────────────────────── */

interface MessageListProps {
    messages: Message[];
    isLoading: boolean;
    onExportTranscript?: () => void;
    onFollowUpClick?: (text: string) => void;
}

export function MessageList({
    messages,
    isLoading,
    onExportTranscript,
    onFollowUpClick,
}: MessageListProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const t = useTranslations('chat');
    const [copied, setCopied] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<
        Record<string, 'up' | 'down' | null>
    >({});
    const [openSourcesId, setOpenSourcesId] = useState<string | null>(null);
    const [expandedCitation, setExpandedCitation] = useState<string | null>(
        null
    );
    const [sidebarCitations, setSidebarCitations] = useState<
        Citation[] | null
    >(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    const handleCopy = (id: string, content: string) => {
        navigator.clipboard.writeText(content).then(() => {
            setCopied(id);
            setTimeout(() => setCopied(null), 1500);
        });
    };

    const handleFeedback = (id: string, value: 'up' | 'down') => {
        setFeedback((prev) => ({
            ...prev,
            [id]: prev[id] === value ? null : value,
        }));
    };

    const openSidebar = (citations: Citation[]) => {
        setSidebarCitations(citations);
        setOpenSourcesId(null);
        setExpandedCitation(null);
    };

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground animate-in fade-in duration-500">
                <div className="bg-primary/5 p-4 rounded-full mb-4">
                    <Sparkles className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold mb-2 text-foreground tracking-tight">
                    Awaqi
                </h2>
                <p className="max-w-sm text-sm">{t('placeholder')}</p>
            </div>
        );
    }

    const lastAssistantIdx = messages.reduceRight(
        (found, msg, idx) =>
            found === -1 && msg.role === 'assistant' ? idx : found,
        -1
    );

    return (
        <>
            <div
                className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
                ref={scrollRef}
            >
                {messages.map((msg, msgIdx) => (
                    <div
                        key={msg.id}
                        className={cn(
                            'flex w-full gap-3',
                            msg.role === 'user'
                                ? 'justify-end'
                                : 'justify-start'
                        )}
                    >
                        {msg.role === 'user' ? (
                            /* ── User bubble ── */
                            <div className="max-w-[80%] rounded-2xl px-5 py-3.5 text-sm shadow-sm bg-primary text-primary-foreground rounded-br-sm">
                                {msg.attachments &&
                                    msg.attachments.length > 0 && (
                                        <div className="mb-3 space-y-2">
                                            {msg.attachments.map((att) => (
                                                <div
                                                    key={att.id}
                                                    className="flex items-center gap-2 text-xs bg-background/20 p-2 rounded-md border border-white/10"
                                                >
                                                    <Paperclip className="w-3.5 h-3.5" />
                                                    <span className="truncate">
                                                        {att.name}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                <div className="whitespace-pre-wrap leading-relaxed">
                                    {msg.content}
                                </div>
                            </div>
                        ) : (
                            /* ── Assistant bubble + action bar ── */
                            <div className="flex flex-col items-start max-w-[80%] gap-1.5">
                                {/* bubble */}
                                <div className="rounded-2xl px-5 py-3.5 text-sm shadow-sm bg-card border border-border/50 text-foreground rounded-bl-sm">
                                    {/* While streaming but no content yet — show status or dots */}
                                    {msg.isStreaming && msg.content === '' && (
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            {msg.statusText ? (
                                                <span className="italic text-xs animate-pulse">
                                                    {msg.statusText}
                                                </span>
                                            ) : (
                                                <>
                                                    <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                                    <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                                    <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce" />
                                                </>
                                            )}
                                        </div>
                                    )}
                                    {(msg.content || !msg.isStreaming) && (
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            p: ({ children }) => (
                                                <p className="mb-2 last:mb-0 leading-relaxed">
                                                    {children}
                                                </p>
                                            ),
                                            h1: ({ children }) => (
                                                <h1 className="text-base font-bold mb-2 mt-3 first:mt-0">
                                                    {children}
                                                </h1>
                                            ),
                                            h2: ({ children }) => (
                                                <h2 className="text-sm font-bold mb-2 mt-3 first:mt-0">
                                                    {children}
                                                </h2>
                                            ),
                                            h3: ({ children }) => (
                                                <h3 className="text-sm font-semibold mb-1.5 mt-2 first:mt-0">
                                                    {children}
                                                </h3>
                                            ),
                                            ul: ({ children }) => (
                                                <ul className="mb-2 ml-4 space-y-1 list-disc">
                                                    {children}
                                                </ul>
                                            ),
                                            ol: ({ children }) => (
                                                <ol className="mb-2 ml-4 space-y-1 list-decimal">
                                                    {children}
                                                </ol>
                                            ),
                                            li: ({ children }) => (
                                                <li className="leading-relaxed">
                                                    {children}
                                                </li>
                                            ),
                                            strong: ({ children }) => (
                                                <strong className="font-semibold">
                                                    {children}
                                                </strong>
                                            ),
                                            em: ({ children }) => (
                                                <em className="italic">
                                                    {children}
                                                </em>
                                            ),
                                            code: ({
                                                children,
                                                className,
                                            }) => {
                                                const isBlock =
                                                    className?.includes(
                                                        'language-'
                                                    );
                                                return isBlock ? (
                                                    <code className="block bg-muted rounded-md px-3 py-2 text-xs font-mono my-2 overflow-x-auto">
                                                        {children}
                                                    </code>
                                                ) : (
                                                    <code className="bg-muted rounded px-1 py-0.5 text-xs font-mono">
                                                        {children}
                                                    </code>
                                                );
                                            },
                                            pre: ({ children }) => (
                                                <pre className="my-2">
                                                    {children}
                                                </pre>
                                            ),
                                            blockquote: ({ children }) => (
                                                <blockquote className="border-l-2 border-primary/40 pl-3 my-2 text-muted-foreground italic">
                                                    {children}
                                                </blockquote>
                                            ),
                                            hr: () => (
                                                <hr className="border-border/50 my-3" />
                                            ),
                                            a: ({ href, children }) => (
                                                <a
                                                    href={href}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-primary underline underline-offset-2 hover:opacity-80"
                                                >
                                                    {children}
                                                </a>
                                            ),
                                            table: ({ children }) => (
                                                <div className="overflow-x-auto my-2">
                                                    <table className="text-xs border-collapse w-full">
                                                        {children}
                                                    </table>
                                                </div>
                                            ),
                                            th: ({ children }) => (
                                                <th className="border border-border/50 px-2 py-1 bg-muted font-semibold text-left">
                                                    {children}
                                                </th>
                                            ),
                                            td: ({ children }) => (
                                                <td className="border border-border/50 px-2 py-1">
                                                    {children}
                                                </td>
                                            ),
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                    )}
                                    {/* Blinking cursor while streaming */}
                                    {msg.isStreaming && msg.content !== '' && (
                                        <span className="inline-block w-0.5 h-4 bg-primary/70 ml-0.5 align-text-bottom animate-[blink_1s_step-end_infinite]" />
                                    )}
                                </div>

                                {/* action bar — hidden while streaming */}
                                {!msg.isStreaming && (
                                <div className="relative flex items-center gap-0.5 px-1">
                                    <button
                                        onClick={() =>
                                            handleCopy(msg.id, msg.content)
                                        }
                                        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                                        title="Copy"
                                    >
                                        <Copy
                                            className={cn(
                                                'w-3.5 h-3.5',
                                                copied === msg.id &&
                                                    'text-green-500'
                                            )}
                                        />
                                    </button>
                                    <button
                                        onClick={() =>
                                            handleFeedback(msg.id, 'up')
                                        }
                                        className={cn(
                                            'p-1.5 rounded-md transition-colors hover:bg-muted/60',
                                            feedback[msg.id] === 'up'
                                                ? 'text-green-500'
                                                : 'text-muted-foreground hover:text-foreground'
                                        )}
                                        title="Helpful"
                                    >
                                        <ThumbsUp className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() =>
                                            handleFeedback(msg.id, 'down')
                                        }
                                        className={cn(
                                            'p-1.5 rounded-md transition-colors hover:bg-muted/60',
                                            feedback[msg.id] === 'down'
                                                ? 'text-red-500'
                                                : 'text-muted-foreground hover:text-foreground'
                                        )}
                                        title="Not helpful"
                                    >
                                        <ThumbsDown className="w-3.5 h-3.5" />
                                    </button>

                                    {/* Confidence score */}
                                    {typeof msg.confidenceScore === 'number' &&
                                        msg.confidenceScore > 0 && (
                                            <ConfidencePill
                                                score={msg.confidenceScore}
                                            />
                                        )}

                                    {/* Sources button */}
                                    {msg.citations &&
                                        msg.citations.length > 0 && (
                                            <div className="relative">
                                                <button
                                                    onClick={() => {
                                                        setOpenSourcesId(
                                                            openSourcesId ===
                                                                msg.id
                                                                ? null
                                                                : msg.id
                                                        );
                                                        setExpandedCitation(
                                                            null
                                                        );
                                                    }}
                                                    className={cn(
                                                        'flex items-center gap-1 p-1.5 rounded-md transition-colors hover:bg-muted/60 text-xs',
                                                        openSourcesId ===
                                                            msg.id
                                                            ? 'text-primary'
                                                            : 'text-muted-foreground hover:text-foreground'
                                                    )}
                                                    title="Sources"
                                                >
                                                    <BookOpen className="w-3.5 h-3.5" />
                                                    <span className="font-medium">
                                                        {msg.citations.length}
                                                    </span>
                                                </button>

                                                {/* Sources popover */}
                                                {openSourcesId === msg.id && (
                                                    <div className="absolute bottom-full left-0 mb-2 w-72 rounded-xl border border-border/60 bg-card shadow-lg z-10 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-150">
                                                        <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
                                                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                                                {t('sources')}
                                                            </span>
                                                            <button
                                                                onClick={() =>
                                                                    setOpenSourcesId(
                                                                        null
                                                                    )
                                                                }
                                                                className="p-0.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60"
                                                            >
                                                                <X className="w-3.5 h-3.5" />
                                                            </button>
                                                        </div>

                                                        <div className="p-2 space-y-1 max-h-52 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                                                            {msg.citations
                                                                .slice(0, 3)
                                                                .map((c, i) => {
                                                                    const key = `${msg.id}:${i}`;
                                                                    const open =
                                                                        expandedCitation ===
                                                                        key;
                                                                    return (
                                                                        <div
                                                                            key={
                                                                                key
                                                                            }
                                                                        >
                                                                            <button
                                                                                type="button"
                                                                                onClick={() =>
                                                                                    setExpandedCitation(
                                                                                        open
                                                                                            ? null
                                                                                            : key
                                                                                    )
                                                                                }
                                                                                className="w-full flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-xs hover:bg-muted/60 transition-colors"
                                                                            >
                                                                                <span className="min-w-0 truncate font-medium text-foreground">
                                                                                    {citationPillTitle(
                                                                                        c,
                                                                                        i
                                                                                    )}
                                                                                </span>
                                                                                {open ? (
                                                                                    <ChevronUp className="h-3 w-3 shrink-0 text-muted-foreground" />
                                                                                ) : (
                                                                                    <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
                                                                                )}
                                                                            </button>
                                                                            {open && (
                                                                                <div className="mx-3 mb-1 space-y-1.5 rounded-lg bg-muted/40 p-2.5 text-xs leading-relaxed">
                                                                                    {(c.proclamation_number ||
                                                                                        c.article_number) && (
                                                                                        <p className="text-muted-foreground font-medium">
                                                                                            {c.proclamation_number && (
                                                                                                <span>
                                                                                                    Proc.{' '}
                                                                                                    {
                                                                                                        c.proclamation_number
                                                                                                    }
                                                                                                </span>
                                                                                            )}
                                                                                            {c.proclamation_number &&
                                                                                                c.article_number && (
                                                                                                    <span>
                                                                                                        {' '}
                                                                                                        ·{' '}
                                                                                                    </span>
                                                                                                )}
                                                                                            {c.article_number && (
                                                                                                <span>
                                                                                                    Art.{' '}
                                                                                                    {
                                                                                                        c.article_number
                                                                                                    }
                                                                                                </span>
                                                                                            )}
                                                                                        </p>
                                                                                    )}
                                                                                    <p className="text-muted-foreground">
                                                                                        Page{' '}
                                                                                        {
                                                                                            c.page
                                                                                        }
                                                                                    </p>
                                                                                    <p className="whitespace-pre-wrap text-foreground">
                                                                                        {
                                                                                            c.text
                                                                                        }
                                                                                    </p>
                                                                                    {c.source_url && (
                                                                                        <a
                                                                                            href={
                                                                                                c.source_url
                                                                                            }
                                                                                            target="_blank"
                                                                                            rel="noopener noreferrer"
                                                                                            className="inline-flex items-center gap-1 text-primary hover:opacity-80 transition-opacity font-medium"
                                                                                        >
                                                                                            <ExternalLink className="w-3 h-3" />
                                                                                            Open
                                                                                        </a>
                                                                                    )}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    );
                                                                })}
                                                        </div>

                                                        {/* View all sources footer */}
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                openSidebar(
                                                                    msg.citations!
                                                                )
                                                            }
                                                            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 border-t border-border/40 text-xs font-medium text-primary hover:bg-primary/5 transition-colors"
                                                        >
                                                            View all{' '}
                                                            {
                                                                msg.citations
                                                                    .length
                                                            }{' '}
                                                            sources
                                                            <ChevronRight className="w-3.5 h-3.5" />
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                    {onExportTranscript && (
                                        <button
                                            onClick={onExportTranscript}
                                            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                                            title="Export transcript"
                                        >
                                            <Download className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                </div>
                                )}

                                {/* Follow-up chips */}
                                {!isLoading &&
                                    !msg.isStreaming &&
                                    msgIdx === lastAssistantIdx &&
                                    msg.followUpSuggestions &&
                                    msg.followUpSuggestions.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mt-2 max-w-[480px] animate-in fade-in slide-in-from-bottom-1 duration-300">
                                            {msg.followUpSuggestions.map(
                                                (chip) => (
                                                    <button
                                                        key={chip}
                                                        type="button"
                                                        onClick={() =>
                                                            onFollowUpClick?.(
                                                                chip
                                                            )
                                                        }
                                                        className="text-xs px-3 py-1.5 rounded-full border border-border/70 bg-muted/40 text-muted-foreground hover:bg-primary/10 hover:border-primary/40 hover:text-foreground transition-all duration-150 text-left leading-snug"
                                                    >
                                                        {chip}
                                                    </button>
                                                )
                                            )}
                                        </div>
                                    )}
                            </div>
                        )}
                    </div>
                ))}

                {isLoading && !messages.some((m) => m.isStreaming) && (
                    <div className="flex justify-start gap-3">
                        <div className="bg-card border border-border/50 text-foreground rounded-2xl rounded-bl-sm px-5 py-3.5 text-sm shadow-sm flex items-center gap-1">
                            <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
                            <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
                            <div className="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce" />
                        </div>
                    </div>
                )}
            </div>

            {/* Sources sidebar overlay */}
            {sidebarCitations && (
                <SourcesSidebar
                    citations={sidebarCitations}
                    onClose={() => setSidebarCitations(null)}
                />
            )}
        </>
    );
}
