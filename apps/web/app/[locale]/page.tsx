import { Hero } from '@/components/landing/Hero';
import { BentoGridDemo } from '@/components/landing/BentoGrid';
import { FeatureShowcase } from '@/components/landing/FeatureShowcase';
import { BottomCTA } from '@/components/landing/BottomCTA';
import { Footer } from '@/components/landing/Footer';
import { Navbar } from '@/components/landing/Navbar';

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/30">
            <Navbar />
            <main className="flex-1 w-full overflow-hidden">
                <Hero />
                <BentoGridDemo />
                <FeatureShowcase />
                <BottomCTA />
            </main>
            <Footer />
        </div>
    );
}
