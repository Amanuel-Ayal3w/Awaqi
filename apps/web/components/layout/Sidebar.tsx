'use client';

import React from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Menu, Plus, MessageSquare, Settings, History, LogOut, LogIn } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/SidebarContext';
import { customerAuthClient } from '@/lib/customer-auth-client';
import { chatApi } from '@/lib/api';
import { getOrCreateSessionId } from '@/lib/chat-session';
import type { ChatMessage } from '@/types/api';

export function Sidebar() {
    const t = useTranslations('common');
    const locale = useLocale();
    const pathname = usePathname();
    const { isOpen, toggleSidebar, isMobileOpen, setMobileOpen } = useSidebar();
    const router = useRouter();
    const { data: session } = customerAuthClient.useSession();

    const user = session?.user;
    const initials = user?.name
        ? user.name.trim().split(' ').map((n: string) => n[0]).slice(0, 2).join('').toUpperCase()
        : '?';

    const handleSignOut = async () => {
        await customerAuthClient.signOut();
        router.push(`/${locale}/chat/login`);
    };

    const [showUserMenu, setShowUserMenu] = React.useState(false);
    const [recentHistory, setRecentHistory] = React.useState<ChatMessage[]>([]);

    React.useEffect(() => {
        const sessionId = getOrCreateSessionId();

        chatApi
            .getHistory(sessionId)
            .then((history) => {
                const latestUserMessages = history
                    .filter((msg) => msg.role === 'user')
                    .slice(-4)
                    .reverse();
                setRecentHistory(latestUserMessages);
            })
            .catch(() => {
                setRecentHistory([]);
            });
    }, []);

    // Inner Component to handle Collapsed/Expanded states
    const SidebarContent = ({ isCollapsed, isMobile = false }: { isCollapsed: boolean; isMobile?: boolean }) => (
        <div className="flex flex-col h-full">
            {/* Top Section: Toggle (Desktop Only) & New Chat */}
            <div className={cn("p-2 pb-0 flex flex-col gap-4", isCollapsed ? "items-center" : "items-stretch")}>

                {/* Internal Toggle - Only visible on Desktop within the sidebar */}
                {!isMobile && (
                    <div className={cn("flex items-center", isCollapsed ? "justify-center" : "px-2 justify-start")}>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={toggleSidebar}
                            title={isCollapsed ? t('expand') : t('collapse')}
                        >
                            <Menu className="h-5 w-5" />
                        </Button>
                    </div>
                )}

                <Button
                    asChild
                    className={cn(
                        "justify-start gap-3 shadow-none border-0 transition-all duration-200",
                        isCollapsed ? "w-10 h-10 p-0 justify-center bg-transparent hover:bg-muted" : "w-full bg-primary/10 text-primary hover:bg-primary/20 hover:text-primary"
                    )}
                    variant={isCollapsed ? "ghost" : "outline"}
                    title={t('newChat')}
                >
                    <Link href={`/${locale}/chat`}>
                        <Plus className="h-5 w-5" />
                        {!isCollapsed && <span className="font-semibold">{t('newChat')}</span>}
                    </Link>
                </Button>
            </div>

            {/* Middle Section: Recent History */}
            {/* Hide History when collapsed to keep UI clean */}
            <div className={cn(
                "flex-1 overflow-hidden flex flex-col mt-4 transition-opacity duration-200",
                isCollapsed ? "opacity-0 invisible h-0" : "opacity-100 visible"
            )}>
                <div className="px-4 py-2">
                    <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        {t('history')}
                    </h2>
                </div>
                <ScrollArea className="flex-1 px-2">
                    <div className="space-y-1">
                        {recentHistory.map((item, index) => (
                            <Button
                                key={`${item.timestamp}-${index}`}
                                variant="ghost"
                                className="w-full justify-start h-auto py-2 px-3 text-sm font-normal text-muted-foreground hover:text-foreground"
                                asChild
                            >
                                <Link href={`/${locale}/chat/history`}>
                                    <MessageSquare className="h-4 w-4 mr-2 shrink-0" />
                                    <span className="truncate text-left">{item.content}</span>
                                </Link>
                            </Button>
                        ))}
                        <Button
                            variant="ghost"
                            className="w-full justify-start h-auto py-2 px-3 text-sm font-normal text-muted-foreground hover:text-foreground mt-2"
                            asChild
                        >
                            <Link href={`/${locale}/chat/history`}>
                                <History className="h-4 w-4 mr-2 shrink-0" />
                                <span className="truncate">{t('viewAllHistory')}</span>
                            </Link>
                        </Button>
                    </div>
                </ScrollArea>
            </div>

            {/* Bottom Section: User + Settings */}
            <div className={cn("p-2 border-t mt-auto space-y-1", isCollapsed ? "flex flex-col items-center" : "block")}>

                {/* User Avatar / Sign In */}
                {user ? (
                    <div className="relative">
                        {/* Upward popup card */}
                        {showUserMenu && (
                            <>
                                {/* Backdrop */}
                                <div
                                    className="fixed inset-0 z-40"
                                    onClick={() => setShowUserMenu(false)}
                                />
                                {/* Popup */}
                                <div className={cn(
                                    "absolute z-50 bottom-full mb-2 bg-popover border border-border rounded-xl shadow-xl p-3 min-w-[180px] animate-in fade-in slide-in-from-bottom-2 duration-150",
                                    isCollapsed ? "left-0" : "left-0 right-0"
                                )}>
                                    <div className="flex items-center gap-3 mb-3 pb-3 border-b border-border">
                                        <div className="h-9 w-9 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-bold shrink-0">
                                            {initials}
                                        </div>
                                        <div className="min-w-0">
                                            <p className="text-sm font-semibold truncate">{user.name}</p>
                                            <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={async () => { setShowUserMenu(false); await handleSignOut(); }}
                                        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm text-destructive hover:bg-destructive/10 transition-colors font-medium"
                                    >
                                        <LogOut className="h-4 w-4" />
                                        Sign out
                                    </button>
                                </div>
                            </>
                        )}

                        {/* Avatar button */}
                        <button
                            onClick={() => setShowUserMenu(v => !v)}
                            className={cn(
                                "flex items-center gap-3 w-full px-2 py-2 rounded-md hover:bg-muted transition-colors",
                                isCollapsed ? "justify-center px-0" : "",
                                showUserMenu && "bg-muted"
                            )}
                            title={user.name ?? 'Account'}
                        >
                            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0 select-none">
                                {initials}
                            </div>
                            {!isCollapsed && (
                                <span className="text-sm font-medium truncate flex-1 text-left">{user.name}</span>
                            )}
                        </button>
                    </div>
                ) : (
                    <Button
                        variant="ghost"
                        className={cn(
                            "justify-start text-muted-foreground hover:text-foreground transition-all duration-200",
                            isCollapsed ? "w-10 h-10 p-0 justify-center" : "w-full"
                        )}
                        title="Sign in"
                        asChild
                    >
                        <Link href={`/${locale}/chat/login`}>
                            <LogIn className={cn("h-5 w-5", !isCollapsed && "mr-3")} />
                            {!isCollapsed && <span>Sign in</span>}
                        </Link>
                    </Button>
                )}

                {/* Settings */}
                <Button
                    variant="ghost"
                    className={cn(
                        "justify-start text-muted-foreground hover:text-foreground transition-all duration-200",
                        isCollapsed ? "w-10 h-10 p-0 justify-center" : "w-full",
                        pathname.startsWith(`/${locale}/chat/settings`) && "bg-secondary text-foreground"
                    )}
                    title={t('settings')}
                    asChild
                >
                    <Link href={`/${locale}/chat/settings`}>
                        <Settings className={cn("h-5 w-5", !isCollapsed && "mr-3")} />
                        {!isCollapsed && t('settings')}
                    </Link>
                </Button>
            </div>
        </div>
    );

    return (
        <>
            {/* Desktop Sidebar - Persistent & Resizable */}
            <aside className={cn(
                "hidden md:flex flex-col border-r bg-muted/30 backdrop-blur-sm transition-all duration-300 ease-in-out overflow-hidden",
                isOpen ? "w-64" : "w-[68px]"
            )}>
                <SidebarContent isCollapsed={!isOpen} />

                {/* Footer Version - Hide on collapse */}
                <div className={cn(
                    "p-2 text-[10px] text-muted-foreground text-center border-t border-border/50 transition-opacity duration-200",
                    !isOpen ? "opacity-0 h-0 p-0" : "opacity-100"
                )}>
                    ERA Support Bot v0.1.0
                </div>
            </aside>

            {/* Mobile Hamburger Menu - Controlled via Context (Triggered from Header) */}
            <Sheet open={isMobileOpen} onOpenChange={setMobileOpen}>
                <SheetContent side="left" className="w-72 p-0">
                    <SheetTitle className="sr-only">{t('appName')}</SheetTitle>
                    <div className="h-full bg-background">
                        <div className="p-4 border-b flex items-center">
                            <div className="h-8 w-8 rounded bg-primary mr-3 flex items-center justify-center text-primary-foreground font-bold">A</div>
                            <span className="font-bold text-lg">Awaqi</span>
                        </div>
                        {/* Mobile always expanded */}
                        <SidebarContent isCollapsed={false} isMobile={true} />
                    </div>
                </SheetContent>
            </Sheet>
        </>
    );
}
