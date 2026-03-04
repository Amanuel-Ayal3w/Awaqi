const SESSION_STORAGE_KEY = 'awaqi_session_id';

export function getOrCreateSessionId(): string {
    if (typeof window === 'undefined') {
        return crypto.randomUUID();
    }

    let id = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!id) {
        id = crypto.randomUUID();
        sessionStorage.setItem(SESSION_STORAGE_KEY, id);
    }

    return id;
}
