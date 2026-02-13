'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface SidebarContextType {
    isOpen: boolean;
    toggleSidebar: () => void;
    closeSidebar: () => void;
    isMobileOpen: boolean;
    toggleMobileOpen: () => void;
    setMobileOpen: (open: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function SidebarProvider({ children }: { children: ReactNode }) {
    // Default to true (open) on desktop
    const [isOpen, setIsOpen] = useState(true);
    // Mobile sheet state
    const [isMobileOpen, setMobileOpen] = useState(false);

    const toggleSidebar = () => setIsOpen((prev) => !prev);
    const closeSidebar = () => setIsOpen(false);

    const toggleMobileOpen = () => setMobileOpen((prev) => !prev);

    return (
        <SidebarContext.Provider value={{
            isOpen,
            toggleSidebar,
            closeSidebar,
            isMobileOpen,
            toggleMobileOpen,
            setMobileOpen
        }}>
            {children}
        </SidebarContext.Provider>
    );
}

export function useSidebar() {
    const context = useContext(SidebarContext);
    if (context === undefined) {
        throw new Error('useSidebar must be used within a SidebarProvider');
    }
    return context;
}
