'use client';

import React, { ReactNode, Suspense } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';

import { SidebarProvider } from '@/contexts/SidebarContext';

export function ClientLayout({ children }: { children: ReactNode }) {
    return (
        <SidebarProvider>
            <div className="flex h-screen overflow-hidden">
                <Suspense>
                    <Sidebar />
                </Suspense>
                <div className="flex-1 flex flex-col overflow-hidden">
                    <Header />
                    <main className="flex-1 overflow-x-hidden overflow-y-auto bg-background p-4 md:p-8">
                        {children}
                    </main>
                </div>
            </div>
        </SidebarProvider>
    );
}
