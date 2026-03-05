const SESSIONS_KEY = 'awaqi_sessions';
const ACTIVE_SESSION_KEY = 'awaqi_active_session';

export interface ChatSessionInfo {
    id: string;
    title: string;
    createdAt: string;
}

export function getAllSessions(): ChatSessionInfo[] {
    if (typeof window === 'undefined') return [];
    try {
        const raw = localStorage.getItem(SESSIONS_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveSessions(sessions: ChatSessionInfo[]) {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
}

export function getActiveSessionId(): string | null {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem(ACTIVE_SESSION_KEY);
}

export function setActiveSession(id: string) {
    sessionStorage.setItem(ACTIVE_SESSION_KEY, id);
}

export function createNewSession(): string {
    const id = crypto.randomUUID();
    sessionStorage.setItem(ACTIVE_SESSION_KEY, id);
    return id;
}

export function updateSessionTitle(id: string, title: string) {
    const sessions = getAllSessions();
    const existing = sessions.find(s => s.id === id);
    if (existing) {
        if (!existing.title || existing.title === id) {
            existing.title = title;
        }
    } else {
        sessions.unshift({ id, title, createdAt: new Date().toISOString() });
    }
    saveSessions(sessions);
    window.dispatchEvent(new Event('awaqi-sessions-updated'));
}

export function getOrCreateSessionId(): string {
    let id = getActiveSessionId();
    if (!id) {
        id = createNewSession();
    }
    return id;
}
