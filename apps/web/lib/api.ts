import axios from "axios";
import { authClient } from "@/lib/auth-client";
import type {
    ChatMessage,
    ChatRequest,
    ChatResponse,
    DocumentStatus,
    FeedbackRequest,
    LogEntryList,
    ScraperStatus,
} from "@/types/api";

const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
});

// Attach the Better Auth session token as a Bearer header on every request.
// For public endpoints (chat) the session will be null — no header is added
// and FastAPI handles those routes without auth.
apiClient.interceptors.request.use(async (config) => {
    const { data } = await authClient.getSession();
    if (data?.session?.token) {
        config.headers.Authorization = `Bearer ${data.session.token}`;
    }
    return config;
});

// Redirect to login on 401 (session expired / revoked)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && typeof window !== "undefined") {
            const locale = window.location.pathname.split("/")[1] ?? "en";
            window.location.href = `/${locale}/login`;
        }
        return Promise.reject(error);
    }
);

// ── Chat API ──────────────────────────────────────────────────────────────────

export const chatApi = {
    send: async (payload: ChatRequest): Promise<ChatResponse> => {
        const { data } = await apiClient.post<ChatResponse>("/v1/chat/send", payload);
        return data;
    },

    getHistory: async (sessionId: string): Promise<ChatMessage[]> => {
        const { data } = await apiClient.get<ChatMessage[]>(
            `/v1/chat/history/${sessionId}`
        );
        return data;
    },

    submitFeedback: async (
        messageId: string,
        payload: FeedbackRequest
    ): Promise<void> => {
        await apiClient.post(`/v1/chat/feedback/${messageId}`, payload);
    },
};

// ── Admin API ─────────────────────────────────────────────────────────────────

export const adminApi = {
    uploadDocument: async (file: File): Promise<DocumentStatus> => {
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await apiClient.post<DocumentStatus>(
            "/v1/admin/upload",
            formData,
            { headers: { "Content-Type": "multipart/form-data" } }
        );
        return data;
    },

    getLogs: async (): Promise<LogEntryList> => {
        const { data } = await apiClient.get<LogEntryList>("/v1/admin/logs");
        return data;
    },

    triggerScraper: async (): Promise<ScraperStatus> => {
        const { data } = await apiClient.post<ScraperStatus>("/v1/admin/scrape");
        return data;
    },
};
