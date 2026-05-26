"use client"

import { Suspense, use } from "react"
import { useSearchParams } from "next/navigation"
import { useLocale } from "next-intl"
import { Loader2 } from "lucide-react"
import { DocumentReviewWorkspace } from "@/components/admin/DocumentReviewWorkspace"
import type { AdminReviewFrom } from "@/lib/admin-routes"

type PageProps = {
    params: Promise<{ id: string; locale: string }>
}

function parseFrom(value: string | null): AdminReviewFrom | null {
    if (value === "scraper" || value === "documents") return value
    return null
}

function ReviewPageInner({ docId }: { docId: string }) {
    const locale = useLocale()
    const searchParams = useSearchParams()
    const from = parseFrom(searchParams.get("from"))

    return <DocumentReviewWorkspace docId={docId} locale={locale} from={from} />
}

export default function DocumentReviewPage({ params }: PageProps) {
    const { id } = use(params)

    return (
        <Suspense
            fallback={
                <div className="flex flex-1 items-center justify-center py-24">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            }
        >
            <ReviewPageInner docId={id} />
        </Suspense>
    )
}
