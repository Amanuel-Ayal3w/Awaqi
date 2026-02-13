import { LoginForm } from '@/components/auth/LoginForm';
import { Navbar } from '@/components/landing/Navbar';
import { useTranslations } from 'next-intl';

export default function LoginPage() {
    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Navbar />
            <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
                <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
                    <LoginForm />
                </div>
            </div>
        </div>
    );
}
