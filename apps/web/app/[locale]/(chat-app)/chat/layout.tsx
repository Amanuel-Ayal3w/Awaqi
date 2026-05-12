'use client';

import { ClientLayout } from '@/components/layout/ClientLayout';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ClientLayout>
            {children}
        </ClientLayout>
    );
}
