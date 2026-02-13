import { Hero } from '@/components/landing/Hero';
import { Features } from '@/components/landing/Features';
import { Navbar } from '@/components/landing/Navbar';

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Navbar />
            <main className="flex-1">
                <Hero />
                <Features />
            </main>
            <footer className="py-8 border-t border-border/40 text-center text-sm text-muted-foreground bg-background/50 backdrop-blur-sm">
                © {new Date().getFullYear()} Revenue Support Bot. All rights reserved.
            </footer>
        </div>
    );
}
