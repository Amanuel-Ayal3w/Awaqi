import type { Citation } from '@/types/api';

export interface Attachment {
    id: string;
    name: string;
    type: 'image' | 'file';
    url?: string;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    attachments?: Attachment[];
    citations?: Citation[];
    /** Follow-up question chips shown below the last assistant message (AWA-30). */
    followUpSuggestions?: string[];
    /** Confidence score (0–1) returned by the RAG pipeline. */
    confidenceScore?: number;
    /** True while streaming — content is being progressively filled in. */
    isStreaming?: boolean;
    /** Tool-call progress text shown while the assistant content is still empty. */
    statusText?: string;
}
