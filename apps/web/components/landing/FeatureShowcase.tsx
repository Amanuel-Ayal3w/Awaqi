'use client';

import { Bot, Globe, Zap, ShieldCheck } from 'lucide-react';

const chatMessages = [
    {
        role: 'agent',
        content: 'Hello! I\'m Awaqi, your AI tax assistant. How can I help you with Ethiopian tax law today?',
    },
    {
        role: 'user',
        content: 'What is the VAT rate for goods in Ethiopia?',
    },
    {
        role: 'agent',
        content: 'The standard VAT rate in Ethiopia is 15%, applied to most taxable goods and services. Some items are exempt or zero-rated under ERCA regulations.',
    },
];

const featureItems = [
    {
        icon: <Globe className="h-4 w-4" />,
        title: 'Multilingual',
        desc: 'Supports Amharic & English seamlessly',
    },
    {
        icon: <Zap className="h-4 w-4" />,
        title: 'Instant',
        desc: 'Real-time answers powered by AI',
    },
    {
        icon: <Bot className="h-4 w-4" />,
        title: 'Smart',
        desc: 'Context-aware, law-based responses',
    },
    {
        icon: <ShieldCheck className="h-4 w-4" />,
        title: 'Secure',
        desc: 'Enterprise-grade data protection',
    },
];

export function FeatureShowcase() {
    return (
        <section id="features" className="py-28 border-t border-white/[0.06]">
            <div className="container">
                {/* Section header */}
                <div className="text-center max-w-2xl mx-auto mb-16">
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-muted-foreground mb-6">
                        ✦ Interactive Demo
                    </span>
                    <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4 leading-tight">
                        Experience AI Tax Support in Real-Time
                    </h2>
                    <p className="text-muted-foreground text-lg">
                        See how Awaqi handles complex tax queries with precision and clarity — in your language.
                    </p>
                </div>

                {/* Demo layout */}
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 max-w-5xl mx-auto">
                    {/* Chat window */}
                    <div className="lg:col-span-3 rounded-2xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
                        {/* Chat header */}
                        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                                    <Bot className="h-4 w-4 text-foreground" />
                                </div>
                                <div>
                                    <p className="text-sm font-semibold leading-none">Awaqi AI</p>
                                    <div className="flex items-center gap-1.5 mt-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                        <span className="text-xs text-muted-foreground">Online</span>
                                    </div>
                                </div>
                            </div>
                            <span className="text-xs text-muted-foreground border border-white/10 rounded-full px-2.5 py-1">
                                Ethiopian Tax Law
                            </span>
                        </div>

                        {/* Messages */}
                        <div className="p-5 space-y-4 min-h-[260px]">
                            {chatMessages.map((msg, i) => (
                                <div
                                    key={i}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${msg.role === 'user'
                                                ? 'bg-white text-black rounded-br-sm font-medium'
                                                : 'bg-white/[0.06] text-foreground rounded-bl-sm border border-white/[0.08]'
                                            }`}
                                    >
                                        {msg.content}
                                    </div>
                                </div>
                            ))}

                            {/* Typing indicator */}
                            <div className="flex justify-start">
                                <div className="bg-white/[0.06] border border-white/[0.08] rounded-2xl rounded-bl-sm px-4 py-3">
                                    <div className="flex gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Input bar */}
                        <div className="px-5 pb-5">
                            <div className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-3">
                                <span className="text-sm text-muted-foreground/50 flex-1">Ask about Ethiopian tax law…</span>
                                <div className="w-6 h-6 rounded-full bg-white/80 flex items-center justify-center">
                                    <svg className="h-3 w-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                                    </svg>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Feature list */}
                    <div className="lg:col-span-2 flex flex-col gap-4">
                        <p className="text-sm text-muted-foreground uppercase tracking-widest font-medium mb-2">
                            What makes it great
                        </p>
                        {featureItems.map((item) => (
                            <div
                                key={item.title}
                                className="flex items-start gap-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 hover:border-white/20 hover:bg-white/[0.04] transition-all duration-200"
                            >
                                <div className="w-8 h-8 rounded-lg border border-white/10 bg-white/5 flex items-center justify-center text-muted-foreground shrink-0">
                                    {item.icon}
                                </div>
                                <div>
                                    <p className="text-sm font-semibold leading-none mb-1">{item.title}</p>
                                    <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                                </div>
                            </div>
                        ))}

                        <div className="mt-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                            <div className="flex items-center gap-2 text-emerald-400 text-xs font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                Active &amp; Ready
                            </div>
                            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                                Awaqi responds instantly in your language, based on the latest ERCA regulations.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
