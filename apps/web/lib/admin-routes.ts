export type AdminReviewFrom = "documents" | "scraper"

export function adminDocumentReviewPath(
    locale: string,
    docId: string,
    from: AdminReviewFrom = "documents"
): string {
    return `/${locale}/admin/documents/${docId}/review?from=${from}`
}

export function adminReviewBackPath(locale: string, from: AdminReviewFrom | null): string {
    if (from === "scraper") return `/${locale}/admin/scraper`
    return `/${locale}/admin/documents`
}
