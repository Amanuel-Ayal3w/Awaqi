export type AdminReviewFrom = "documents" | "scraper" | "review-queue"

export function adminDocumentReviewPath(
    locale: string,
    docId: string,
    from: AdminReviewFrom = "documents"
): string {
    return `/${locale}/admin/documents/${docId}/review?from=${from}`
}

export function adminReviewBackPath(locale: string, from: AdminReviewFrom | null): string {
    if (from === "scraper") return `/${locale}/admin/scraper`
    if (from === "review-queue") return `/${locale}/admin/review-queue`
    return `/${locale}/admin/documents`
}
