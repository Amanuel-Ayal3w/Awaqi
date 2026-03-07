import axios from "axios";
import { authClient } from "@/lib/auth-client";
import { customerAuthClient } from "@/lib/customer-auth-client";
import type {
    AdminDocumentList,
    AdminUserList,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    DocumentStatus,
    FeedbackRequest,
    LogEntryList,
    ScraperJobStatus,
    ScraperStatus,
} from "@/types/api";

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

    getScraperStatus: async (jobId: string): Promise<ScraperJobStatus> => {
        const { data } = await apiClient.get<ScraperJobStatus>(
            `/v1/admin/scrape/status?job_id=${encodeURIComponent(jobId)}`
        );
        return data;
    },

    listDocuments: async (limit = 100): Promise<AdminDocumentList> => {
        const { data } = await apiClient.get<AdminDocumentList>(
            `/v1/admin/documents?limit=${limit}`
        );
        return data;
    },

    listUsers: async (): Promise<AdminUserList> => {
        const { data } = await apiClient.get<AdminUserList>("/v1/admin/users");
        return data;
    },

    deleteUser: async (userId: string): Promise<void> => {
        await apiClient.delete(`/v1/admin/users/${userId}`);
    },
};
