import { customerAuth } from "@/lib/customer-auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(customerAuth);
