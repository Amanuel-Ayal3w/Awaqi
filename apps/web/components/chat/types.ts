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
}
