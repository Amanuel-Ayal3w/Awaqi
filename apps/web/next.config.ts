import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';
import path from 'path';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const nextConfig: NextConfig = {
    // Pin the workspace root to this directory so Next.js / webpack resolve
    // @/* path aliases correctly in CI (prevents the home-dir yarn.lock
    // from being mistaken for the monorepo root).
    outputFileTracingRoot: path.join(__dirname, '../../'),
};

export default withNextIntl(nextConfig);

