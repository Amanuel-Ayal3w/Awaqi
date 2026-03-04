import { CustomerSignUpForm } from '@/components/auth/CustomerSignUpForm';
import Link from 'next/link';

export default function ChatSignUpPage() {
    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
            {/* Subtle branding */}
            <Link href="/" className="mb-8 flex items-center gap-1 group">
                <span className="text-2xl font-bold tracking-tight text-foreground">Awaqi</span>
                <span className="text-2xl font-bold text-muted-foreground/50 group-hover:text-muted-foreground transition-colors">.</span>
            </Link>

            <div className="w-full max-w-[400px]">
                <CustomerSignUpForm />
            </div>
        </div>
    );
}
