import createIntlMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";

const LOCALES = ["en", "am"] as const;
const DEFAULT_LOCALE = "en";

const intlMiddleware = createIntlMiddleware({
  locales: LOCALES,
  defaultLocale: DEFAULT_LOCALE,
  localePrefix: "as-needed",
});

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protect all /[locale]/admin/* paths.
  // We check for the Better Auth session cookie here (Edge-compatible, no DB).
  // The actual cryptographic validation of the token happens inside FastAPI's
  // get_current_admin dependency on every admin API call.
  if (pathname.includes("/admin")) {
    const sessionToken = request.cookies.get("better-auth.session_token")?.value;

    if (!sessionToken) {
      // Derive the locale from the path so the redirect lands on the right login page
      const parts = pathname.split("/").filter(Boolean);
      const locale = (LOCALES as readonly string[]).includes(parts[0])
        ? parts[0]
        : DEFAULT_LOCALE;

      return NextResponse.redirect(new URL(`/${locale}/login`, request.url));
    }
  }

  // Delegate all locale routing to next-intl
  return intlMiddleware(request);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
