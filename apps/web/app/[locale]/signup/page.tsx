import { CustomerSignUpForm } from '@/components/auth/CustomerSignUpForm';
import { Navbar } from '@/components/landing/Navbar';

export default function SignUpPage() {
    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Navbar />
            <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
                <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[400px]">
                    <CustomerSignUpForm />
                </div>
            </div>
        </div>
    );
}
