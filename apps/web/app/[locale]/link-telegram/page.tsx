"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { customerAuthClient } from "@/lib/customer-auth-client";
import apiClient from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type PageState =
    | { status: "loading" }
    | { status: "unauthenticated" }
    | { status: "ready"; email: string }
    | { status: "confirming" }
    | { status: "success"; displayName: string }
    | { status: "error"; message: string };

export default function LinkTelegramPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const token = searchParams.get("token");

    const [state, setState] = useState<PageState>({ status: "loading" });
    const [countdown, setCountdown] = useState(3);

    useEffect(() => {
        if (!token) {
            setState({ status: "error", message: "No link token found. Please use /link in the Telegram bot again." });
            return;
        }

        customerAuthClient.getSession().then(({ data }) => {
            if (!data?.user) {
                setState({ status: "unauthenticated" });
            } else {
                setState({ status: "ready", email: data.user.email ?? "" });
            }
        });
    }, [token]);

    const handleConfirm = async () => {
        if (!token) return;
        setState({ status: "confirming" });

        try {
            const { data: session } = await customerAuthClient.getSession();
            const bearerToken = session?.session?.token;

            const { data: confirmed } = await apiClient.post(
                `${API_BASE}/v1/auth/telegram/link-confirm`,
                { token },
                {
                    headers: bearerToken ? { Authorization: `Bearer ${bearerToken}` } : {},
                    withCredentials: true,
                }
            );
            setState({ status: "success", displayName: confirmed.display_name ?? "" });
        } catch (err: unknown) {
            const message =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                "Something went wrong. Please try again.";
            setState({ status: "error", message });
        }
    };

    useEffect(() => {
        if (state.status !== "success") return;
        if (countdown <= 0) {
            window.location.href = "https://t.me/ERATaxBot";
            return;
        }
        const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
        return () => clearTimeout(t);
    }, [state.status, countdown]);

    const loginUrl = `./chat/login?redirect=/link-telegram?token=${token}`;

    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
            <Link href="/" className="mb-8 flex items-center gap-1 group">
                <span className="text-2xl font-bold tracking-tight text-foreground">Awaqi</span>
                <span className="text-2xl font-bold text-muted-foreground/50 group-hover:text-muted-foreground transition-colors">.</span>
            </Link>

            <div className="w-full max-w-[400px] rounded-xl border border-border bg-card p-8 shadow-sm space-y-6">
                <div className="space-y-1 text-center">
                    <h1 className="text-2xl font-bold tracking-tight">Connect Telegram</h1>
                    <p className="text-sm text-muted-foreground">
                        Link your Telegram account to your Awaqi web account so your conversation history syncs across both.
                    </p>
                </div>

                {state.status === "loading" && (
                    <p className="text-center text-sm text-muted-foreground animate-pulse">Checking session…</p>
                )}

                {state.status === "unauthenticated" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground text-center">
                            You need to be logged in to link your Telegram account.
                        </p>
                        <Link
                            href={loginUrl}
                            className="block w-full text-center rounded-lg bg-primary text-primary-foreground py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
                        >
                            Log in to Awaqi
                        </Link>
                        <Link
                            href="./chat/signup"
                            className="block w-full text-center rounded-lg border border-border py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
                        >
                            Create an account
                        </Link>
                    </div>
                )}

                {state.status === "ready" && (
                    <div className="space-y-4">
                        <div className="rounded-lg bg-muted/50 border border-border p-4 text-sm space-y-1">
                            <p className="font-medium">Signed in as</p>
                            <p className="text-muted-foreground truncate">{state.email}</p>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Click below to connect your Telegram account to this Awaqi account. Your future Telegram conversations will be linked to your profile.
                        </p>
                        <button
                            onClick={handleConfirm}
                            className="w-full rounded-lg bg-primary text-primary-foreground py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
                        >
                            Connect Telegram
                        </button>
                    </div>
                )}

                {state.status === "confirming" && (
                    <p className="text-center text-sm text-muted-foreground animate-pulse">Linking your account…</p>
                )}

                {state.status === "success" && (
                    <div className="space-y-4 text-center">
                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                            <svg className="h-6 w-6 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                        <div>
                            <p className="font-semibold">Telegram connected!</p>
                            {state.displayName && (
                                <p className="text-sm text-muted-foreground mt-1">
                                    Signed in as <span className="font-medium text-foreground">{state.displayName}</span>
                                </p>
                            )}
                            <p className="text-sm text-muted-foreground mt-1">
                                A confirmation has been sent to your Telegram chat.
                            </p>
                            <p className="text-sm text-muted-foreground mt-3">
                                Redirecting to Telegram in <span className="font-medium text-foreground">{countdown}</span>s…
                            </p>
                        </div>
                        <a
                            href="https://t.me/ERATaxBot"
                            className="block w-full text-center rounded-lg bg-primary text-primary-foreground py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
                        >
                            Open Telegram now
                        </a>
                        <Link
                            href="./chat"
                            className="block w-full text-center rounded-lg border border-border py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
                        >
                            Go to Web Chat
                        </Link>
                    </div>
                )}

                {state.status === "error" && (
                    <div className="space-y-4">
                        <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive">
                            {state.message}
                        </div>
                        <Link
                            href="/"
                            className="block w-full text-center rounded-lg border border-border py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
                        >
                            Go to Home
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}
