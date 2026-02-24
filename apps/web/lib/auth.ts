import { betterAuth } from "better-auth";
import { Pool } from "pg";

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL_SYNC,
  }),
  emailAndPassword: {
    enabled: true,
  },
  advanced: {
    database: {
      // Generate UUID v4 IDs — keeps ba_user.id consistent with
      // every other UUID primary key in the schema.
      generateId: "uuid",
    },
  },
  user: {
    additionalFields: {
      role: {
        type: "string",
        defaultValue: "editor",
        required: false,
        input: false,
      },
      isActive: {
        type: "boolean",
        // fieldName tells Better Auth to use "is_active" as the DB column name
        fieldName: "is_active",
        defaultValue: true,
        required: false,
        input: false,
      },
    },
  },
});

export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.Session.user;
