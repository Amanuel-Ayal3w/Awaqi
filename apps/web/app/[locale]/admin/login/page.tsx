import { AdminLoginForm } from '@/components/auth/AdminLoginForm';
import { Navbar } from '@/components/landing/Navbar';

export default function AdminLoginPage() {
    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Navbar />
            <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
                <div className="mx-auto flex w-full flex-col justify-center sm:w-[420px]">
                    <AdminLoginForm />
                </div>
            </div>
        </div>
    );
}
