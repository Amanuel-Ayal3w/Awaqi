import { randomBytes } from 'crypto';

const MIN_SECRET_LENGTH = 32;

const BLOCKED_SECRETS = new Set([
    'change-me-in-production',
    'changeme',
    'secret',
    'password',
    'test',
    'development',
]);

function estimateEntropy(secret: string): number {
    const uniqueChars = new Set(secret).size;
    return uniqueChars / secret.length;
}

function isSecretWeak(secret: string): boolean {
    if (secret.length < MIN_SECRET_LENGTH) {
        return true;
    }

    if (BLOCKED_SECRETS.has(secret.toLowerCase())) {
        return true;
    }

    if (estimateEntropy(secret) < 0.35) {
        return true;
    }

    return false;
}

let cachedDevSecret: string | null = null;

function getOrCreateDevSecret(): string {
    if (cachedDevSecret) {
        return cachedDevSecret;
    }

    cachedDevSecret = randomBytes(48).toString('base64url');
    return cachedDevSecret;
}

export function getValidatedBetterAuthSecret(): string {
    const secret = process.env.BETTER_AUTH_SECRET;
    const isProduction = process.env.NODE_ENV === 'production';

    if (!secret || isSecretWeak(secret)) {
        if (isProduction) {
            if (!secret) {
                throw new Error(
                    'BETTER_AUTH_SECRET is required. Generate one with `npx @better-auth/cli secret` or `openssl rand -base64 32`.'
                );
            }

            if (secret.length < MIN_SECRET_LENGTH) {
                throw new Error(
                    `BETTER_AUTH_SECRET must be at least ${MIN_SECRET_LENGTH} characters long.`
                );
            }

            if (BLOCKED_SECRETS.has(secret.toLowerCase())) {
                throw new Error('BETTER_AUTH_SECRET is too weak. Use a random generated secret.');
            }

            throw new Error('BETTER_AUTH_SECRET appears low-entropy. Use a random generated secret.');
        }

        const devSecret = getOrCreateDevSecret();
        process.env.BETTER_AUTH_SECRET = devSecret;

        console.warn(
            '[auth] Using an auto-generated BETTER_AUTH_SECRET for local development. Set a strong BETTER_AUTH_SECRET in your .env.local to keep sessions stable across restarts.'
        );

        return devSecret;
    }

    return secret;
}
