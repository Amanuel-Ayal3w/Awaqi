'use client';

import React from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sheet, SheetClose, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Menu, Plus, MessageSquare, Settings, History } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/SidebarContext';

// Mock Data for History
const mockHistory = [
    { id: '1', title: 'VAT Registration Guide', date: 'Today' },
    { id: '2', title: 'Tax Clearance Certificate', date: 'Yesterday' },
    { id: '3', title: 'Penalty Waiver Request', date: 'Previous 7 Days' },
    { id: '4', title: 'Employment Income Tax', date: 'Previous 30 Days' },
];

export function Sidebar() {
    const t = useTranslations('common');
    const locale = useLocale();
    const pathname = usePathname();
    const { isOpen, toggleSidebar, isMobileOpen, setMobileOpen } = useSidebar();

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
                    <Link href={`/${locale}`}>
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
                        {mockHistory.map((item) => (
                            <Button
                                key={item.id}
                                variant="ghost"
                                className="w-full justify-start h-auto py-2 px-3 text-sm font-normal text-muted-foreground hover:text-foreground"
                                asChild
                            >
                                <Link href={`/${locale}/history/${item.id}`}>
                                    <MessageSquare className="h-4 w-4 mr-2 shrink-0" />
                                    <span className="truncate text-left">{item.title}</span>
                                </Link>
                            </Button>
                        ))}
                        <Button
                            variant="ghost"
                            className="w-full justify-start h-auto py-2 px-3 text-sm font-normal text-muted-foreground hover:text-foreground mt-2"
                            asChild
                        >
                            <Link href={`/${locale}/history`}>
                                <History className="h-4 w-4 mr-2 shrink-0" />
                                <span className="truncate">{t('viewAllHistory')}</span>
                            </Link>
                        </Button>
                    </div>
                </ScrollArea>
            </div>

            {/* Bottom Section: Settings */}
            <div className={cn("p-2 border-t mt-auto", isCollapsed ? "flex justify-center" : "block")}>
                <Button
                    variant="ghost"
                    className={cn(
                        "justify-start text-muted-foreground hover:text-foreground transition-all duration-200",
                        isCollapsed ? "w-10 h-10 p-0 justify-center" : "w-full",
                        pathname.startsWith(`/${locale}/dashboard/settings`) && "bg-secondary text-foreground"
                    )}
                    title={t('settings')}
                    asChild
                >
                    <Link href={`/${locale}/dashboard/settings`}>
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
