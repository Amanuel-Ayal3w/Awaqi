"use client"

import Link from "next/link"
import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    ExternalLink,
    FileText,
    Loader2,
    RefreshCw,
    Save,
    Sparkles,
} from "lucide-react"
import { useDocumentReview } from "@/hooks/useDocumentReview"
import { adminReviewBackPath, type AdminReviewFrom } from "@/lib/admin-routes"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"

type DocumentReviewWorkspaceProps = {
    docId: string
    locale: string
    from: AdminReviewFrom | null
}

function StatusBadge({ status }: { status: string }) {
    const normalized = status.replace(/_/g, " ")
    return (
        <Badge
            variant="outline"
            className={cn(
                "font-normal capitalize",
                status === "indexed" &&
                    "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
                status === "requires_manual_review" &&
                    "border-amber-500/50 bg-amber-500/15 text-amber-800 dark:text-amber-200",
                status === "failed" && "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
                (status === "pending" || status === "processing") &&
                    "border-sky-500/40 bg-sky-500/10 text-sky-800 dark:text-sky-200"
            )}
        >
            {normalized || "unknown"}
        </Badge>
    )
}

function OcrMeter({ pct }: { pct: number | null }) {
    if (pct == null) return null
    const low = pct < 70
    return (
        <div className="flex min-w-[140px] flex-col gap-1">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
                <span>OCR confidence</span>
                <span className={cn("font-semibold tabular-nums", low && "text-amber-600 dark:text-amber-400")}>
                    {pct}%
                </span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-muted">
                <div
                    className={cn(
                        "h-full rounded-full transition-all duration-700",
                        low ? "bg-amber-500" : "bg-emerald-500"
                    )}
                    style={{ width: `${Math.min(100, pct)}%` }}
                />
            </div>
        </div>
    )
}

function PdfPanel({
    pdfUrl,
    pdfLoading,
    sourceUrl,
}: {
    pdfUrl: string | null
    pdfLoading: boolean
    sourceUrl?: string | null
}) {
    return (
        <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border/80 bg-[hsl(240_4%_6%)] shadow-inner">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-2.5">
                <span className="text-xs font-medium uppercase tracking-widest text-white/50">
                    Source PDF
                </span>
                {sourceUrl ? (
                    <a
                        href={sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-white/60 transition-colors hover:text-white"
                    >
                        MoR link
                        <ExternalLink className="h-3 w-3" />
                    </a>
                ) : null}
            </div>
            <div className="relative min-h-0 flex-1">
                {pdfLoading && !pdfUrl ? (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[hsl(240_4%_6%)]">
                        <Loader2 className="h-8 w-8 animate-spin text-white/40" />
                        <p className="text-xs text-white/40">Loading PDF…</p>
                    </div>
                ) : null}
                {pdfUrl ? (
                    <iframe title="Document PDF" src={pdfUrl} className="h-full w-full border-0" />
                ) : (
                    <div className="flex h-full items-center justify-center p-8 text-center text-sm text-white/40">
                        PDF preview unavailable
                    </div>
                )}
            </div>
        </div>
    )
}

function EditorPanel({
    editorText,
    setEditorText,
    textLoading,
    textSource,
    disabled,
}: {
    editorText: string
    setEditorText: (v: string) => void
    textLoading: boolean
    textSource?: string
    disabled: boolean
}) {
    const charCount = editorText.length
    const lineCount = editorText ? editorText.split("\n").length : 0

    return (
        <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
                <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <div>
                        <p className="text-sm font-semibold leading-none">Transcript</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Edit OCR output here — this is what gets indexed
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                    {textSource ? (
                        <span className="rounded-md border px-2 py-0.5">{textSource}</span>
                    ) : null}
                    <span>{lineCount} lines</span>
                    <span>{charCount.toLocaleString()} chars</span>
                </div>
            </div>

            <div className="relative min-h-0 flex-1">
                {textLoading ? (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-card/90 backdrop-blur-sm">
                        <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">Running OCR / loading text…</p>
                        <p className="max-w-xs text-center text-xs text-muted-foreground/80">
                            Large Amharic PDFs can take up to a minute. The PDF panel loads in parallel.
                        </p>
                    </div>
                ) : null}
                <textarea
                    value={editorText}
                    onChange={(e) => setEditorText(e.target.value)}
                    disabled={disabled || textLoading}
                    spellCheck={false}
                    placeholder="Extracted text will appear here. Compare with the PDF on the left and correct encoding, numbers, and Amharic script before indexing."
                    className={cn(
                        "h-full min-h-[280px] w-full resize-none border-0 bg-transparent px-4 py-4",
                        "font-mono text-[13px] leading-relaxed text-foreground",
                        "focus-visible:outline-none focus-visible:ring-0",
                        "placeholder:text-muted-foreground/60",
                        "disabled:cursor-not-allowed disabled:opacity-60"
                    )}
                />
            </div>
        </div>
    )
}

export function DocumentReviewWorkspace({ docId, locale, from }: DocumentReviewWorkspaceProps) {
    const backHref = adminReviewBackPath(locale, from)
    const {
        detail,
        preview,
        pdfUrl,
        shellLoading,
        textLoading,
        pdfLoading,
        editorText,
        setEditorText,
        ingestBusy,
        retryBusy,
        error,
        isDirty,
        status,
        canRetry,
        ocrPct,
        handleRetryOcr,
        handleIngestText,
    } = useDocumentReview(docId)

    const title = detail?.title ?? preview?.title ?? "Document review"
    const needsReview = preview?.requires_manual_review ?? status === "requires_manual_review"
    const actionsDisabled = ingestBusy || retryBusy || textLoading
    const amhMissing = !(preview?.tesseract_langs_installed ?? []).includes("amh")
    const textQualityBad = preview?.text_quality_warning ?? false
    const extractionModes = preview?.pages?.map((p) => p.extraction_mode) ?? []
    const usedPdfTextOnly =
        extractionModes.length > 0 && extractionModes.every((m) => m === "pdf_text")

    if (shellLoading) {
        return (
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
                <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Opening document workspace…</p>
            </div>
        )
    }

    if (!detail) {
        return (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
                <p className="text-muted-foreground">Document not found.</p>
                <Button variant="outline" asChild>
                    <Link href={backHref}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Link>
                </Button>
            </div>
        )
    }

    return (
        <div className="document-review flex min-h-0 flex-1 flex-col">
            {/* Ambient header band */}
            <div
                className="shrink-0 border-b px-5 py-4"
                style={{
                    background:
                        "linear-gradient(135deg, hsl(var(--background)) 0%, hsl(38 92% 50% / 0.06) 50%, hsl(var(--background)) 100%)",
                }}
            >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1 space-y-3">
                        <Link
                            href={backHref}
                            className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                        >
                            <ArrowLeft className="h-3.5 w-3.5" />
                            {from === "scraper" ? "Back to scraper" : "Back to documents"}
                        </Link>
                        <h1 className="text-xl font-semibold leading-snug tracking-tight md:text-2xl">
                            {title}
                        </h1>
                        <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge status={status} />
                            {needsReview ? (
                                <Badge className="gap-1 border-amber-500/50 bg-amber-500/20 text-amber-950 hover:bg-amber-500/25 dark:text-amber-100">
                                    <AlertTriangle className="h-3 w-3" />
                                    {preview?.review_reason?.replace(/_/g, " ") ?? "Manual review"}
                                </Badge>
                            ) : status === "indexed" ? (
                                <Badge
                                    variant="outline"
                                    className="gap-1 border-emerald-500/40 text-emerald-700 dark:text-emerald-300"
                                >
                                    <CheckCircle2 className="h-3 w-3" />
                                    Indexed
                                </Badge>
                            ) : null}
                            {preview?.chunk_count != null ? (
                                <span className="text-xs text-muted-foreground">
                                    {preview.chunk_count} chunks
                                </span>
                            ) : null}
                        </div>
                        {(detail.ingest_error || preview?.ingest_error) && (
                            <p className="text-xs text-muted-foreground">
                                Ingest: {detail.ingest_error ?? preview?.ingest_error}
                            </p>
                        )}
                    </div>
                    <OcrMeter pct={ocrPct} />
                </div>
                {error ? (
                    <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                        {error}
                    </p>
                ) : null}
                {amhMissing ? (
                    <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
                        <strong>Tesseract Amharic pack missing.</strong> Installed languages:{" "}
                        {(preview?.tesseract_langs_installed ?? []).join(", ") || "none"}. OCR is
                        using <code className="text-xs">{preview?.ocr_langs_resolved ?? "eng"}</code>{" "}
                        only — install <code className="text-xs">tesseract-ocr-amh</code> (Linux) or{" "}
                        <code className="text-xs">brew install tesseract-lang</code> (macOS), then use{" "}
                        <strong>Retry OCR</strong>.
                    </p>
                ) : null}
                {textQualityBad ? (
                    <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
                        <strong>Extracted text looks corrupt</strong>
                        {usedPdfTextOnly
                            ? " (likely a broken PDF embedded text layer, not real OCR)."
                            : " (OCR output has almost no Amharic script)."}
                        {preview?.text_quality_reasons?.length ? (
                            <> Signals: {preview.text_quality_reasons.join(", ")}.</>
                        ) : null}{" "}
                        Tesseract confidence only measures how sure the engine is about the
                        characters it guessed — not whether the text is correct. Edit the transcript
                        or fix OCR and re-index.
                    </p>
                ) : null}
            </div>

            {/* Workspace — desktop split / mobile tabs */}
            <div className="min-h-0 flex-1 p-4">
                <div className="hidden h-[calc(100vh-14rem)] min-h-[420px] grid-cols-2 gap-4 lg:grid">
                    <PdfPanel
                        pdfUrl={pdfUrl}
                        pdfLoading={pdfLoading}
                        sourceUrl={detail.source_url}
                    />
                    <EditorPanel
                        editorText={editorText}
                        setEditorText={setEditorText}
                        textLoading={textLoading}
                        textSource={preview?.text_source}
                        disabled={actionsDisabled}
                    />
                </div>

                <div className="flex h-[calc(100vh-14rem)] min-h-[420px] flex-col lg:hidden">
                    <Tabs defaultValue="pdf" className="flex min-h-0 flex-1 flex-col">
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="pdf">PDF</TabsTrigger>
                            <TabsTrigger value="text" className="gap-1.5">
                                Transcript
                                {isDirty ? (
                                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                                ) : null}
                            </TabsTrigger>
                        </TabsList>
                        <TabsContent value="pdf" className="mt-3 min-h-0 flex-1 data-[state=active]:flex">
                            <PdfPanel
                                pdfUrl={pdfUrl}
                                pdfLoading={pdfLoading}
                                sourceUrl={detail.source_url}
                            />
                        </TabsContent>
                        <TabsContent value="text" className="mt-3 min-h-0 flex-1 data-[state=active]:flex">
                            <EditorPanel
                                editorText={editorText}
                                setEditorText={setEditorText}
                                textLoading={textLoading}
                                textSource={preview?.text_source}
                                disabled={actionsDisabled}
                            />
                        </TabsContent>
                    </Tabs>
                </div>
            </div>

            {/* Sticky actions */}
            <div className="shrink-0 border-t bg-background/95 px-5 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <p className="max-w-xl text-xs text-muted-foreground">
                        <Sparkles className="mr-1 inline h-3.5 w-3.5 text-amber-500" />
                        Compare the PDF with the transcript, fix Amharic and numbers, then save. Use{" "}
                        <strong className="font-medium text-foreground">Retry OCR</strong> to re-run
                        extraction, or <strong className="font-medium text-foreground">Force index</strong>{" "}
                        to index despite low confidence.
                    </p>
                    <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                        {isDirty ? (
                            <span className="mr-1 text-xs text-amber-600 dark:text-amber-400">
                                Unsaved edits
                            </span>
                        ) : null}
                        <Separator orientation="vertical" className="hidden h-8 sm:block" />
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={retryBusy || !canRetry || actionsDisabled}
                            onClick={() => void handleRetryOcr(false)}
                        >
                            {retryBusy ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <RefreshCw className="mr-2 h-4 w-4" />
                            )}
                            Retry OCR
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={retryBusy || !canRetry || actionsDisabled}
                            onClick={() => void handleRetryOcr(true)}
                        >
                            Force index
                        </Button>
                        <Button
                            size="sm"
                            disabled={ingestBusy || !editorText.trim() || actionsDisabled}
                            onClick={() => void handleIngestText()}
                            className="min-w-[140px]"
                        >
                            {ingestBusy ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Save className="mr-2 h-4 w-4" />
                            )}
                            Save &amp; index
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
