import { createAuthClient } from "better-auth/react";

/**
 * Client-side Better Auth client for end customers.
 *
 * Points to /api/customer-auth (not /api/auth which is admin-only).
 * Use this in all customer-facing pages (signup, login, chat).
 */
export const customerAuthClient = createAuthClient({
    baseURL: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
    basePath: "/api/customer-auth",
});
