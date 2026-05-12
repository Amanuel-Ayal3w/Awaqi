#!/usr/bin/env node
/**
 * Create or update a Better Auth admin user (ba_user + ba_account) with role superadmin.
 * Uses the same password hashing as better-auth (scrypt via better-auth/crypto).
 *
 * Environment:
 *   DATABASE_URL_SYNC — required (PostgreSQL URL, same as Next / Better Auth)
 *   SUPERADMIN_EMAIL — default admin@awaqi.local
 *   SUPERADMIN_PASSWORD — default ChangeMeStrong123!
 *   SUPERADMIN_NAME — default Superadmin
 *
 * Loads `.env` / `.env.local` from the monorepo root and from `apps/web/` (same pattern as
 * Next.js: later files override earlier). Existing shell variables are never overwritten.
 *
 * Run from apps/web: npm run seed:superadmin
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";
import { randomUUID } from "node:crypto";
import { hashPassword } from "better-auth/crypto";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = join(__dirname, "..");
const repoRoot = join(webRoot, "..", "..");

/**
 * @param {string} content
 * @returns {Record<string, string>}
 */
function parseDotenv(content) {
    /** @type {Record<string, string>} */
    const out = {};
    for (let line of content.split(/\r?\n/)) {
        line = line.trim();
        if (!line || line.startsWith("#")) continue;
        if (line.startsWith("export ")) line = line.slice(7).trim();
        const eq = line.indexOf("=");
        if (eq === -1) continue;
        const key = line.slice(0, eq).trim();
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
        let val = line.slice(eq + 1).trim();
        if (
            (val.startsWith('"') && val.endsWith('"')) ||
            (val.startsWith("'") && val.endsWith("'"))
        ) {
            val = val.slice(1, -1).replace(/\\n/g, "\n");
        }
        out[key] = val;
    }
    return out;
}

function applyDotenvFiles() {
    const paths = [
        join(repoRoot, ".env"),
        join(repoRoot, ".env.local"),
        join(webRoot, ".env"),
        join(webRoot, ".env.local"),
    ];
    /** @type {Record<string, string>} */
    const merged = {};
    for (const p of paths) {
        if (!existsSync(p)) continue;
        Object.assign(merged, parseDotenv(readFileSync(p, "utf8")));
    }
    for (const [k, v] of Object.entries(merged)) {
        if (process.env[k] === undefined) process.env[k] = v;
    }
}

applyDotenvFiles();

const conn = process.env.DATABASE_URL_SYNC;
if (!conn) {
    console.error("DATABASE_URL_SYNC is required");
    process.exit(1);
}

const email = (process.env.SUPERADMIN_EMAIL ?? "admin@awaqi.local").trim().toLowerCase();
const password = process.env.SUPERADMIN_PASSWORD ?? "ChangeMeStrong123!";
const displayName = process.env.SUPERADMIN_NAME ?? "Superadmin";

const pool = new pg.Pool({ connectionString: conn });

try {
    const hashed = await hashPassword(password);
    const client = await pool.connect();
    try {
        const existing = await client.query(`SELECT id FROM ba_user WHERE email = $1`, [email]);

        if (existing.rowCount > 0 && existing.rows[0]) {
            const userId = existing.rows[0].id;
            await client.query(
                `UPDATE ba_user SET role = 'superadmin', name = $2, "emailVerified" = true, "updatedAt" = now() WHERE id = $1`,
                [userId, displayName],
            );
            const acc = await client.query(
                `SELECT id FROM ba_account WHERE "userId" = $1 AND "providerId" = 'credential'`,
                [userId],
            );
            if (acc.rowCount > 0 && acc.rows[0]) {
                await client.query(`UPDATE ba_account SET password = $2, "updatedAt" = now() WHERE id = $1`, [
                    acc.rows[0].id,
                    hashed,
                ]);
                console.log(`Updated superadmin credentials for ${email} (${userId})`);
            } else {
                const accId = randomUUID();
                await client.query(
                    `INSERT INTO ba_account (id, "userId", "accountId", "providerId", password, "createdAt", "updatedAt")
                     VALUES ($1, $2, $3, 'credential', $4, now(), now())`,
                    [accId, userId, String(userId), hashed],
                );
                console.log(`Added credential account for ${email} (${userId})`);
            }
        } else {
            const userId = randomUUID();
            await client.query(
                `INSERT INTO ba_user (id, name, email, "emailVerified", image, role, is_active, "createdAt", "updatedAt")
                 VALUES ($1, $2, $3, true, NULL, 'superadmin', true, now(), now())`,
                [userId, displayName, email],
            );
            const accId = randomUUID();
            await client.query(
                `INSERT INTO ba_account (id, "userId", "accountId", "providerId", password, "createdAt", "updatedAt")
                 VALUES ($1, $2, $3, 'credential', $4, now(), now())`,
                [accId, userId, String(userId), hashed],
            );
            console.log(`Created superadmin ${email} (${userId})`);
        }
    } finally {
        client.release();
    }
} finally {
    await pool.end();
}
