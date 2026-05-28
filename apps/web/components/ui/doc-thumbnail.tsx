"use client"

import { useEffect, useRef, useState } from "react"
import { FileText, Image as ImageIcon } from "lucide-react"
import { apiClient } from "@/lib/api"

interface DocThumbnailProps {
    /** Full path to the authenticated thumbnail endpoint, e.g. /v1/admin/documents/{id}/thumbnail */
    thumbnailUrl?: string | null
    title: string
    /** Placeholder icon when thumbnail is unavailable */
    fallbackKind?: "image" | "text"
    className?: string
}

/**
 * Fetches a backend thumbnail endpoint (which requires auth) via axios and
 * renders the result as a blob URL so credentials are included automatically.
 */
export function DocThumbnail({
    thumbnailUrl,
    title,
    fallbackKind = "text",
    className = "h-14 w-10 rounded border object-cover",
}: DocThumbnailProps) {
    const [objectUrl, setObjectUrl] = useState<string | null>(null)
    const [failed, setFailed] = useState(false)
    const prevUrl = useRef<string | null>(null)

    useEffect(() => {
        if (!thumbnailUrl) {
            setFailed(true)
            return
        }
        let alive = true
        setFailed(false)
        setObjectUrl(null)

        apiClient
            .get<Blob>(thumbnailUrl, { responseType: "blob" })
            .then((res) => {
                if (!alive) return
                const url = URL.createObjectURL(res.data)
                prevUrl.current = url
                setObjectUrl(url)
            })
            .catch(() => {
                if (alive) setFailed(true)
            })

        return () => {
            alive = false
            if (prevUrl.current) {
                URL.revokeObjectURL(prevUrl.current)
                prevUrl.current = null
            }
        }
    }, [thumbnailUrl])

    if (objectUrl) {
        return (
            <img
                src={objectUrl}
                alt={`Preview: ${title}`}
                className={className}
                draggable={false}
            />
        )
    }

    return (
        <div className="flex h-14 w-10 items-center justify-center rounded border bg-muted/50">
            {fallbackKind === "image" || failed ? (
                <ImageIcon className="h-4 w-4 text-muted-foreground" />
            ) : (
                <FileText className="h-4 w-4 text-muted-foreground" />
            )}
        </div>
    )
}
