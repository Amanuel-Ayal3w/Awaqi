import { Hero } from '@/components/landing/Hero';
import { Logos } from '@/components/landing/Logos';
import { Features } from '@/components/landing/Features';
import { HowItWorks } from '@/components/landing/HowItWorks';
import { Testimonials } from '@/components/landing/Testimonials';
import { FAQ } from '@/components/landing/FAQ';
import { CTA } from '@/components/landing/CTA';
import { Footer } from '@/components/landing/Footer';
import { Navbar } from '@/components/landing/Navbar';

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Navbar />
            <main className="flex-1">
                <Hero />
                <Logos />
                <Features />
                <HowItWorks />
                <Testimonials />
                <FAQ />
                <CTA />
            </main>
            <Footer />
        </div>
    );
}
