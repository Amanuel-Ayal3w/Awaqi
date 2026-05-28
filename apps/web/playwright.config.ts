import { defineConfig, devices } from '@playwright/test';

const webPort = 3100;
const apiPort = 8000;

const webEnv = {
    BETTER_AUTH_SECRET: process.env.BETTER_AUTH_SECRET ?? 'e2e-test-auth-secret-32chars!!',
    DATABASE_URL_SYNC:
        process.env.DATABASE_URL_SYNC ??
        'postgresql://postgres:postgres@localhost:5432/awaqi_db_test',
    NEXT_PUBLIC_APP_URL: `http://127.0.0.1:${webPort}`,
    NEXT_PUBLIC_API_URL: `http://127.0.0.1:${apiPort}`,
};

const apiEnv = {
    DATABASE_URL:
        process.env.TEST_DATABASE_URL ??
        'postgresql+asyncpg://postgres:postgres@localhost:5432/awaqi_db_test',
    REDIS_URL: process.env.REDIS_URL ?? 'redis://localhost:6379/0',
    SESSION_TOKEN_SECRET: process.env.SESSION_TOKEN_SECRET ?? 'e2e-test-secret',
};

/**
 * E2E tests use Playwright (browser automation).
 * Servers start automatically unless already running locally (reuseExistingServer).
 */
export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? 'github' : 'list',
    use: {
        baseURL: `http://127.0.0.1:${webPort}`,
        trace: 'on-first-retry',
    },
    projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
    webServer: [
        {
            command:
                'cd ../.. && uv sync --package api && uv run --package api uvicorn apps.api.main:app --host 127.0.0.1 --port 8000',
            url: `http://127.0.0.1:${apiPort}/health`,
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
            env: apiEnv,
        },
        {
            command: 'npm run dev',
            url: `http://127.0.0.1:${webPort}`,
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
            env: webEnv,
        },
    ],
});
