'use client';

import { useTranslations } from 'next-intl';
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";

export function FAQ() {
    const t = useTranslations('landing');

    const faqs = [
        {
            question: "Is the tax advice legally binding?",
            answer: "No, the Ethio Revenue Bot provides information based on current tax laws for guidance only. For legal matters, always consult with a certified tax professional or the Ministry of Revenue."
        },
        {
            question: "Is my financial data secure?",
            answer: "Yes. We do not store any personal financial data submitted during conversations. All chats are private and encrypted."
        },
        {
            question: "Does it support languages other than Amharic?",
            answer: "Currently, we support English and Amharic. We are working on adding Afaan Oromoo and Tigrinya in future updates."
        },
        {
            question: "Can I use it on Telegram?",
            answer: "Yes! Our Telegram bot (@ERATaxBot) offers the same powerful features as the web dashboard for on-the-go access."
        }
    ];

    return (
        <section className="py-24 bg-muted/30">
            <div className="container max-w-4xl">
                <div className="text-center mb-16">
                    <h2 className="text-3xl font-bold tracking-tight mb-4">{t('faqTitle')}</h2>
                    <p className="text-muted-foreground text-lg">{t('faqSubtitle')}</p>
                </div>

                <Accordion type="single" collapsible className="w-full">
                    {faqs.map((faq, index) => (
                        <AccordionItem value={`item-${index}`} key={index}>
                            <AccordionTrigger className="text-left text-base font-medium">
                                {faq.question}
                            </AccordionTrigger>
                            <AccordionContent className="text-muted-foreground leading-relaxed">
                                {faq.answer}
                            </AccordionContent>
                        </AccordionItem>
                    ))}
                </Accordion>
            </div>
        </section>
    );
}
