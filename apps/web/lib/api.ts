import axios from "axios";
import { authClient } from "@/lib/auth-client";
import { customerAuthClient } from "@/lib/customer-auth-client";
import type {
    AdminAnalytics,
    AdminDocumentContentPreview,
    AdminDocumentDetail,
    AdminDocumentList,
    AdminScrapeResult,
    AdminScraperConfig,
    AdminScraperConfigPatch,
    AdminScraperRunList,
    AdminScraperStatus,
    AdminSystemHealth,
    AdminTelegramClearResult,
    AdminTelegramConfig,
    AdminTelegramConfigPatch,
    AdminTelegramMessageList,
    AdminTelegramRunList,
    AdminTelegramScrapeResult,
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

    getScraperStatus: async (): Promise<AdminScraperStatus> => {
        const { data } = await apiClient.get<AdminScraperStatus>("/v1/admin/scraper/status");
        return data;
    },

    getScraperRuns: async (limit = 20): Promise<AdminScraperRunList> => {
        const { data } = await apiClient.get<AdminScraperRunList>("/v1/admin/scraper/runs", {
            params: { limit },
        });
        return data;
    },

    getScraperConfig: async (): Promise<AdminScraperConfig> => {
        const { data } = await apiClient.get<AdminScraperConfig>("/v1/admin/scraper/config");
        return data;
    },

    patchScraperConfig: async (
        patch: AdminScraperConfigPatch
    ): Promise<AdminScraperConfig> => {
        const { data } = await apiClient.patch<AdminScraperConfig>(
            "/v1/admin/scraper/config",
            patch
        );
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
        offset?: number;
        scraped_only?: boolean;
        uploaded_by?: string;
    }): Promise<AdminDocumentList> => {
        const params = new URLSearchParams();
        const limit = options?.limit ?? 100;
        params.set("limit", String(limit));
        if (options?.offset != null) {
            params.set("offset", String(options.offset));
        }
        if (options?.scraped_only) {
            params.set("scraped_only", "true");
        }
        if (options?.uploaded_by) {
            params.set("uploaded_by", options.uploaded_by);
        }
        const { data } = await apiClient.get<AdminDocumentList>(
            `/v1/admin/documents?${params.toString()}`
        );
        return data;
    },

    getDocumentContent: async (docId: string): Promise<AdminDocumentContentPreview> => {
        const { data } = await apiClient.get<AdminDocumentContentPreview>(
            `/v1/admin/documents/${docId}/content`,
            { timeout: 300_000 }
        );
        return data;
    },

    fetchDocumentPdfBlob: async (docId: string): Promise<Blob> => {
        const { data } = await apiClient.get<Blob>(`/v1/admin/documents/${docId}/file`, {
            responseType: "blob",
            timeout: 120_000,
            maxContentLength: 50 * 1024 * 1024,
        });
        return data;
    },

    retryDocumentIngest: async (
        docId: string,
        options?: { force_index?: boolean }
    ): Promise<DocumentStatus> => {
        const q = options?.force_index ? "?force_index=true" : "";
        const { data } = await apiClient.post<DocumentStatus>(
            `/v1/admin/documents/${docId}/retry-ingest${q}`
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

    getTelegramConfig: async (): Promise<AdminTelegramConfig> => {
        const { data } = await apiClient.get<AdminTelegramConfig>("/v1/admin/telegram/config");
        return data;
    },

    patchTelegramConfig: async (
        body: AdminTelegramConfigPatch
    ): Promise<AdminTelegramConfig> => {
        const { data } = await apiClient.patch<AdminTelegramConfig>(
            "/v1/admin/telegram/config",
            body
        );
        return data;
    },

    triggerTelegramScrape: async (): Promise<AdminTelegramScrapeResult> => {
        const { data } = await apiClient.post<AdminTelegramScrapeResult>(
            "/v1/admin/telegram/scrape"
        );
        return data;
    },

    getTelegramRuns: async (limit = 20): Promise<AdminTelegramRunList> => {
        const { data } = await apiClient.get<AdminTelegramRunList>(
            `/v1/admin/telegram/runs?limit=${limit}`
        );
        return data;
    },

    listTelegramMessages: async (options?: {
        limit?: number;
        offset?: number;
        channel?: string;
        message_type?: string;
        document_status?: string;
        ingest_filter?: string;
        search?: string;
    }): Promise<AdminTelegramMessageList> => {
        const params = new URLSearchParams();
        params.set("limit", String(options?.limit ?? 500));
        params.set("offset", String(options?.offset ?? 0));
        if (options?.channel) params.set("channel", options.channel);
        if (options?.message_type) params.set("message_type", options.message_type);
        if (options?.document_status) params.set("document_status", options.document_status);
        if (options?.ingest_filter) params.set("ingest_filter", options.ingest_filter);
        if (options?.search) params.set("search", options.search);
        const { data } = await apiClient.get<AdminTelegramMessageList>(
            `/v1/admin/telegram/messages?${params.toString()}`
        );
        return data;
    },

    clearTelegramMessages: async (options?: {
        channel?: string;
        delete_documents?: boolean;
    }): Promise<AdminTelegramClearResult> => {
        const params = new URLSearchParams();
        if (options?.channel) params.set("channel", options.channel);
        if (options?.delete_documents === false) params.set("delete_documents", "false");
        const { data } = await apiClient.delete<AdminTelegramClearResult>(
            `/v1/admin/telegram/messages/clear?${params.toString()}`
        );
        return data;
    },

    deleteTelegramMessage: async (
        rowId: string,
        options?: { delete_document?: boolean }
    ): Promise<void> => {
        const q =
            options?.delete_document === false ? "?delete_document=false" : "";
        await apiClient.delete(`/v1/admin/telegram/messages/${rowId}${q}`);
    },

    reingestTelegramMessage: async (
        rowId: string,
        options?: { force_index?: boolean }
    ): Promise<{ status: string }> => {
        const q = options?.force_index ? "?force_index=true" : "";
        const { data } = await apiClient.post<{ status: string }>(
            `/v1/admin/telegram/messages/${rowId}/reingest${q}`
        );
        return data;
    },
};
