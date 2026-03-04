import { betterAuth } from "better-auth";
import { Pool } from "pg";
import { getValidatedBetterAuthSecret } from "@/lib/auth-secret";

const betterAuthSecret = getValidatedBetterAuthSecret();

/**
 * Customer-facing Better Auth instance.
 *
 * Completely separate from the admin `auth` instance in auth.ts:
 *  - Uses cu_user / cu_session / cu_account / cu_verification tables
 *  - Mounted at /api/customer-auth  (NOT /api/auth)
 *  - Has NO role or is_active fields — customers are always active
 */
export const customerAuth = betterAuth({
    secret: betterAuthSecret,
    baseURL: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
    database: new Pool({
        connectionString: process.env.DATABASE_URL_SYNC,
    }),
    emailAndPassword: {
        enabled: true,
    },
    advanced: {
        cookiePrefix: "awaqi-customer",
        // Generate UUID v4 IDs to match the UUID primary key columns in cu_* tables
        database: {
            generateId: () => crypto.randomUUID(),
        },
    },
    basePath: "/api/customer-auth",
    // Map Better Auth's default table names to our cu_* prefixed tables
    user: {
        modelName: "cu_user",
    },
    session: {
        modelName: "cu_session",
    },
    account: {
        modelName: "cu_account",
    },
    verification: {
        modelName: "cu_verification",
    },
});

export type CustomerSession = typeof customerAuth.$Infer.Session;
export type CustomerUser = typeof customerAuth.$Infer.Session.user;
