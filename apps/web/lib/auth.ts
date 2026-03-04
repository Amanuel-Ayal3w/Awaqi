import { betterAuth } from "better-auth";
import { Pool } from "pg";
import { getValidatedBetterAuthSecret } from "@/lib/auth-secret";

const betterAuthSecret = getValidatedBetterAuthSecret();

export const auth = betterAuth({
  secret: betterAuthSecret,
  baseURL: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  database: new Pool({
    connectionString: process.env.DATABASE_URL_SYNC,
  }),
  emailAndPassword: {
    enabled: true,
  },
  advanced: {
    // Generate UUID v4 IDs to match the UUID primary key columns in ba_* tables
    database: {
      generateId: () => crypto.randomUUID(),
    },
  },
  // Map Better Auth's default table names to our ba_* prefixed tables
  user: {
    modelName: "ba_user",
    additionalFields: {
      role: {
        type: "string",
        defaultValue: "editor",
        required: false,
        input: false,
      },
      isActive: {
        type: "boolean",
        fieldName: "is_active",
        defaultValue: true,
        required: false,
        input: false,
      },
    },
  },
  session: {
    modelName: "ba_session",
  },
  account: {
    modelName: "ba_account",
  },
  verification: {
    modelName: "ba_verification",
  },
});


export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.Session.user;
