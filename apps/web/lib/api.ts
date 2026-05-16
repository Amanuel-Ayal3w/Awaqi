import axios from "axios";
import { authClient } from "@/lib/auth-client";
import { customerAuthClient } from "@/lib/customer-auth-client";
import type {
    AdminAnalytics,
    AdminDocumentDetail,
    AdminDocumentList,
    AdminScrapeResult,
    AdminSystemHealth,
    AdminUserItem,
    AdminUserList,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    DocumentStatus,
    FeedbackRequest,
    LogEntryList,
} from "@/types/api";

export interface ChatSendOptions {
    payload: ChatRequest;
    sessionToken?: string | null;
}

const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    withCredentials: true,
});

// Attach the correct Better Auth session token as a Bearer header.
// Admin endpoints use authClient, user endpoints use customerAuthClient.
apiClient.interceptors.request.use(async (config) => {
    const isAdminApi = config.url?.startsWith('/v1/admin');

    if (isAdminApi) {
        const { data } = await authClient.getSession();
        if (data?.session?.token) {
            config.headers.Authorization = `Bearer ${data.session.token}`;
        }
    } else {
        const { data } = await customerAuthClient.getSession();
        if (data?.session?.token) {
            config.headers.Authorization = `Bearer ${data.session.token}`;
        }
    }

    return config;
});

// Redirect to the appropriate login page on 401 (session expired / revoked)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && typeof window !== "undefined") {
            const isAdminApi = error.config?.url?.startsWith('/v1/admin');
            const pathFirstSegment = window.location.pathname.split("/").filter(Boolean)[0];
            const locale = pathFirstSegment === "en" || pathFirstSegment === "am" ? pathFirstSegment : "en";
            window.location.href = isAdminApi ? `/${locale}/admin/login` : `/${locale}/login`;
        }
        return Promise.reject(error);
    }
);

// ── Chat API ──────────────────────────────────────────────────────────────────

export const chatApi = {
    send: async (payload: ChatRequest, sessionToken?: string | null): Promise<ChatResponse> => {
        const headers: Record<string, string> = {};
        if (sessionToken) {
            headers["X-Session-Token"] = sessionToken;
        }
        const { data } = await apiClient.post<ChatResponse>("/v1/chat/send", payload, { headers });
        return data;
    },

    getHistory: async (sessionId: string, sessionToken?: string | null): Promise<ChatMessage[]> => {
        const headers: Record<string, string> = {};
        if (sessionToken) {
            headers["X-Session-Token"] = sessionToken;
        }
        const { data } = await apiClient.get<ChatMessage[]>(
            `/v1/chat/history/${sessionId}`,
            { headers },
        );
        return data;
    },

    submitFeedback: async (
        messageId: string,
        payload: FeedbackRequest
    ): Promise<void> => {
        await apiClient.post(`/v1/chat/feedback/${messageId}`, payload);
    },

    exportTranscript: async (
        sessionId: string,
        sessionToken?: string | null
    ): Promise<string> => {
        const headers: Record<string, string> = {};
        if (sessionToken) {
            headers["X-Session-Token"] = sessionToken;
        }
        const { data } = await apiClient.get<string>(`/v1/chat/export/${sessionId}`, {
            headers,
            responseType: "text",
        });
        return data;
    },
};

// ── Admin API ─────────────────────────────────────────────────────────────────

export const adminApi = {
    uploadDocument: async (
        file: File,
        options?: { overwrite?: boolean }
    ): Promise<DocumentStatus> => {
        const formData = new FormData();
        formData.append("file", file);
        const q =
            options?.overwrite === true ? "?overwrite=true" : "";
        const { data } = await apiClient.post<DocumentStatus>(
            `/v1/admin/upload${q}`,
            formData,
            { headers: { "Content-Type": "multipart/form-data" } }
        );
        return data;
    },

    getDocument: async (docId: string): Promise<AdminDocumentDetail> => {
        const { data } = await apiClient.get<AdminDocumentDetail>(
            `/v1/admin/documents/${docId}`
        );
        return data;
    },

    triggerScrape: async (): Promise<AdminScrapeResult> => {
        const { data } = await apiClient.post<AdminScrapeResult>("/v1/admin/scrape");
        return data;
    },

    getLogs: async (): Promise<LogEntryList> => {
        const { data } = await apiClient.get<LogEntryList>("/v1/admin/logs");
        return data;
    },

    getAnalytics: async (): Promise<AdminAnalytics> => {
        const { data } = await apiClient.get<AdminAnalytics>("/v1/admin/analytics");
        return data;
    },

    getSystemHealth: async (): Promise<AdminSystemHealth> => {
        const { data } = await apiClient.get<AdminSystemHealth>("/v1/admin/system-health");
        return data;
    },

    listDocuments: async (options?: {
        limit?: number;
        uploaded_by?: string;
    }): Promise<AdminDocumentList> => {
        const params = new URLSearchParams();
        const limit = options?.limit ?? 100;
        params.set("limit", String(limit));
        if (options?.uploaded_by) {
            params.set("uploaded_by", options.uploaded_by);
        }
        const { data } = await apiClient.get<AdminDocumentList>(
            `/v1/admin/documents?${params.toString()}`
        );
        return data;
    },

    ingestPlainText: async (docId: string, text: string): Promise<DocumentStatus> => {
        const { data } = await apiClient.post<DocumentStatus>(
            `/v1/admin/documents/${docId}/ingest-text`,
            text,
            { headers: { "Content-Type": "text/plain;charset=utf-8" } }
        );
        return data;
    },

    patchDocument: async (
        docId: string,
        body: { uploaded_by_id?: string | null }
    ): Promise<AdminDocumentDetail> => {
        const { data } = await apiClient.patch<AdminDocumentDetail>(
            `/v1/admin/documents/${docId}`,
            body
        );
        return data;
    },

    listUsers: async (): Promise<AdminUserList> => {
        const { data } = await apiClient.get<AdminUserList>("/v1/admin/users");
        return data;
    },

    patchUser: async (
        userId: string,
        body: { role?: string; is_active?: boolean }
    ): Promise<AdminUserItem> => {
        const { data } = await apiClient.patch<AdminUserItem>(
            `/v1/admin/users/${userId}`,
            body
        );
        return data;
    },

    deleteUser: async (userId: string): Promise<void> => {
        await apiClient.delete(`/v1/admin/users/${userId}`);
    },
};
