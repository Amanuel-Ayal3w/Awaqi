"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { adminApi } from "@/lib/api"
import type { AdminDocumentContentPreview, AdminDocumentDetail } from "@/types/api"

export function useDocumentReview(docId: string | undefined) {
    const [detail, setDetail] = useState<AdminDocumentDetail | null>(null)
    const [preview, setPreview] = useState<AdminDocumentContentPreview | null>(null)
    const [pdfUrl, setPdfUrl] = useState<string | null>(null)
    const [shellLoading, setShellLoading] = useState(false)
    const [textLoading, setTextLoading] = useState(false)
    const [pdfLoading, setPdfLoading] = useState(false)
    const [editorText, setEditorText] = useState("")
    const [ingestBusy, setIngestBusy] = useState(false)
    const [retryBusy, setRetryBusy] = useState(false)
    const [deleteBusy, setDeleteBusy] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const pdfUrlRef = useRef<string | null>(null)
    const loadGenRef = useRef(0)
    const [baselineText, setBaselineText] = useState("")

    const revokePdfUrl = useCallback(() => {
        if (pdfUrlRef.current) {
            URL.revokeObjectURL(pdfUrlRef.current)
            pdfUrlRef.current = null
        }
        setPdfUrl(null)
    }, [])

    const reloadAll = useCallback(
        async (targetDocId: string) => {
            const gen = ++loadGenRef.current
            setError(null)
            setPreview(null)
            setEditorText("")
            setBaselineText("")
            revokePdfUrl()
            setShellLoading(true)
            setTextLoading(true)
            setPdfLoading(true)

            try {
                const d = await adminApi.getDocument(targetDocId)
                if (gen !== loadGenRef.current) return
                setDetail(d)
                setShellLoading(false)
            } catch (err: unknown) {
                if (gen !== loadGenRef.current) return
                setError(err instanceof Error ? err.message : "Failed to load document")
                setShellLoading(false)
                setTextLoading(false)
                setPdfLoading(false)
                return
            }

            void (async () => {
                try {
                    const content = await adminApi.getDocumentContent(targetDocId)
                    if (gen !== loadGenRef.current) return
                    setPreview(content)
                    const text = content.full_text ?? ""
                    setBaselineText(text)
                    setEditorText(text)
                } catch (err: unknown) {
                    if (gen !== loadGenRef.current) return
                    setError(
                        (prev) =>
                            prev ??
                            (err instanceof Error ? err.message : "Failed to load extracted text")
                    )
                } finally {
                    if (gen === loadGenRef.current) setTextLoading(false)
                }
            })()

            void (async () => {
                try {
                    const blob = await adminApi.fetchDocumentPdfBlob(targetDocId)
                    if (gen !== loadGenRef.current) return
                    const url = URL.createObjectURL(blob)
                    pdfUrlRef.current = url
                    setPdfUrl(url)
                } catch {
                    if (gen !== loadGenRef.current) return
                } finally {
                    if (gen === loadGenRef.current) setPdfLoading(false)
                }
            })()
        },
        [revokePdfUrl]
    )

    useEffect(() => {
        if (!docId) {
            loadGenRef.current += 1
            revokePdfUrl()
            setDetail(null)
            setPreview(null)
            setEditorText("")
            setBaselineText("")
            setError(null)
            setShellLoading(false)
            setTextLoading(false)
            setPdfLoading(false)
            return
        }

        void reloadAll(docId)

        return () => {
            loadGenRef.current += 1
            revokePdfUrl()
        }
    }, [docId, reloadAll, revokePdfUrl])

    const handleRetryOcr = useCallback(
        async (forceIndex: boolean) => {
            if (!docId) return
            setRetryBusy(true)
            setError(null)
            try {
                await adminApi.retryDocumentIngest(docId, { force_index: forceIndex })
                await reloadAll(docId)
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Retry failed")
            } finally {
                setRetryBusy(false)
            }
        },
        [docId, reloadAll]
    )

    const handleIngestText = useCallback(async () => {
        if (!docId || !editorText.trim()) return
        setIngestBusy(true)
        setError(null)
        try {
            await adminApi.ingestPlainText(docId, editorText)
            await reloadAll(docId)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Re-index failed")
        } finally {
            setIngestBusy(false)
        }
    }, [docId, editorText, reloadAll])

    const handleDeleteDocument = useCallback(async () => {
        if (!docId) return
        setDeleteBusy(true)
        setError(null)
        try {
            await adminApi.deleteDocument(docId)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Delete failed")
            throw err
        } finally {
            setDeleteBusy(false)
        }
    }, [docId])

    const isDirty = editorText !== baselineText
    const status = (detail?.status ?? preview?.status ?? "").toLowerCase()
    const canRetry = preview?.has_stored_pdf ?? Boolean(detail?.storage_path?.trim())
    const ocrPct =
        preview?.mean_ocr_confidence != null
            ? Math.round(preview.mean_ocr_confidence * 100)
            : null

    return {
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
        deleteBusy,
        error,
        isDirty,
        status,
        canRetry,
        ocrPct,
        handleRetryOcr,
        handleIngestText,
        handleDeleteDocument,
        reloadAll,
    }
}
