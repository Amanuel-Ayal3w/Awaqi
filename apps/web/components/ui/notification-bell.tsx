'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, ExternalLink, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { announcementsApi } from '@/lib/api';
import type { Announcement } from '@/types/api';

const STORAGE_KEY = 'awaqi_notifications_last_seen';
const POLL_INTERVAL_MS = 5 * 60 * 1000; // poll every 5 minutes

function getLastSeenIso(): string {
    if (typeof window === 'undefined') return new Date(0).toISOString();
    return localStorage.getItem(STORAGE_KEY) ?? new Date(0).toISOString();
}

function setLastSeenNow() {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
}

function timeAgo(isoDate: string): string {
    const diff = Date.now() - new Date(isoDate).getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}

export function NotificationBell() {
    const [open, setOpen] = useState(false);
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const panelRef = useRef<HTMLDivElement>(null);

    const fetchUnreadCount = useCallback(async () => {
        try {
            const since = getLastSeenIso();
            const { unread_count } = await announcementsApi.unreadCount(since);
            setUnreadCount(unread_count);
        } catch {
            // silently ignore — user may not be logged in yet
        }
    }, []);

    const fetchAnnouncements = useCallback(async () => {
        setLoading(true);
        try {
            const { announcements: items } = await announcementsApi.list({ limit: 20 });
            setAnnouncements(items);
        } catch {
            // ignore
        } finally {
            setLoading(false);
        }
    }, []);

    // Poll unread count every 5 minutes
    useEffect(() => {
        fetchUnreadCount();
        const id = setInterval(fetchUnreadCount, POLL_INTERVAL_MS);
        return () => clearInterval(id);
    }, [fetchUnreadCount]);

    // Close panel when clicking outside
    useEffect(() => {
        if (!open) return;
        function handleClick(e: MouseEvent) {
            if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    function handleOpen() {
        if (!open) {
            fetchAnnouncements();
            setOpen(true);
        } else {
            setOpen(false);
        }
    }

    function handleMarkAllRead() {
        setLastSeenNow();
        setUnreadCount(0);
    }

    return (
        <div className="relative" ref={panelRef}>
            {/* Bell button */}
            <button
                onClick={handleOpen}
                aria-label="Notifications"
                className={cn(
                    'relative inline-flex h-9 w-9 items-center justify-center rounded-md',
                    'text-muted-foreground transition-colors',
                    'hover:bg-accent hover:text-accent-foreground',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    open && 'bg-accent text-accent-foreground'
                )}
            >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                    <span
                        className={cn(
                            'absolute -top-0.5 -right-0.5',
                            'flex h-4 w-4 items-center justify-center',
                            'rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground',
                            'ring-2 ring-background'
                        )}
                    >
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown panel */}
            {open && (
                <div
                    className={cn(
                        'absolute right-0 top-11 z-50',
                        'w-[360px] max-w-[calc(100vw-2rem)]',
                        'rounded-lg border bg-popover shadow-lg',
                        'flex flex-col overflow-hidden'
                    )}
                >
                    {/* Panel header */}
                    <div className="flex items-center justify-between border-b px-4 py-3">
                        <div>
                            <p className="text-sm font-semibold">Notifications</p>
                            <p className="text-xs text-muted-foreground">
                                Tax &amp; regulatory announcements
                            </p>
                        </div>
                        <div className="flex items-center gap-1">
                            {unreadCount > 0 && (
                                <button
                                    onClick={handleMarkAllRead}
                                    className="text-xs text-primary hover:underline px-2 py-1 rounded"
                                >
                                    Mark all read
                                </button>
                            )}
                            <button
                                onClick={() => setOpen(false)}
                                className="rounded p-1 hover:bg-accent text-muted-foreground"
                                aria-label="Close"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    </div>

                    {/* Notification list */}
                    <div className="max-h-[420px] overflow-y-auto">
                        {loading && (
                            <div className="flex items-center justify-center py-10">
                                <span className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                            </div>
                        )}

                        {!loading && announcements.length === 0 && (
                            <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-muted-foreground">
                                <Bell className="h-8 w-8 opacity-30" />
                                <p className="text-sm">No announcements yet</p>
                                <p className="text-xs opacity-70">
                                    New tax regulations will appear here
                                </p>
                            </div>
                        )}

                        {!loading &&
                            announcements.map((item) => (
                                <AnnouncementItem key={item.id} item={item} />
                            ))}
                    </div>

                    {/* Footer */}
                    {!loading && announcements.length > 0 && (
                        <div className="border-t px-4 py-2 text-center">
                            <p className="text-xs text-muted-foreground">
                                Showing the {announcements.length} most recent announcement
                                {announcements.length !== 1 ? 's' : ''}
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function AnnouncementItem({ item }: { item: Announcement }) {
    return (
        <div className="group border-b last:border-0 px-4 py-3 hover:bg-accent/50 transition-colors">
            {/* Document title */}
            <p className="text-sm font-medium leading-snug line-clamp-2 text-foreground">
                {item.doc_title}
            </p>

            {/* Summary */}
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed line-clamp-3">
                {item.summary}
            </p>

            {/* Footer row */}
            <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-[11px] text-muted-foreground/70">
                    {timeAgo(item.created_at)}
                </span>

                {item.source_url && (
                    <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                    >
                        View document
                        <ExternalLink className="h-3 w-3" />
                    </a>
                )}
            </div>
        </div>
    );
}
