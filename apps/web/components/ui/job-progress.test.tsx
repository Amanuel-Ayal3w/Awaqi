import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { JobProgress } from './job-progress';

class MockEventSource {
    static instances: MockEventSource[] = [];
    url: string;
    onmessage: ((ev: MessageEvent) => void) | null = null;
    onerror: (() => void) | null = null;

    constructor(url: string) {
        this.url = url;
        MockEventSource.instances.push(this);
    }

    close() {
        /* noop */
    }

    emit(data: object) {
        this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
    }
}

vi.mock('@/lib/auth-client', () => ({
    authClient: {
        getSession: vi.fn().mockResolvedValue({ data: { session: { token: 'test-token' } } }),
    },
}));

describe('JobProgress', () => {
    beforeEach(() => {
        MockEventSource.instances = [];
        vi.stubGlobal('EventSource', MockEventSource);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('renders queued state and connects to progress SSE', async () => {
        render(<JobProgress jobId="job-123" label="Uploading…" />);

        expect(screen.getByText('Uploading…')).toBeInTheDocument();
        expect(screen.getByText('0%')).toBeInTheDocument();

        await waitFor(() => {
            expect(MockEventSource.instances.length).toBeGreaterThan(0);
        });

        const es = MockEventSource.instances[0];
        expect(es.url).toContain('/v1/admin/progress/job-123');
        expect(es.url).toContain('token=test-token');
    });

    it('updates UI and calls onDone when job completes', async () => {
        const onDone = vi.fn();
        render(<JobProgress jobId="job-456" onDone={onDone} />);

        await waitFor(() => expect(MockEventSource.instances[0]).toBeDefined());

        await act(async () => {
            MockEventSource.instances[0].emit({
                job_id: 'job-456',
                pct: 100,
                step: 'Finished',
                status: 'done',
            });
        });

        expect(screen.getByText('Complete')).toBeInTheDocument();
        expect(screen.getByText('100%')).toBeInTheDocument();
        expect(onDone).toHaveBeenCalledWith('done');
    });
});
