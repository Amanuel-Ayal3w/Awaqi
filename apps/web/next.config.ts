import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';
import path from 'path';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const nextConfig: NextConfig = {
    // Prevent root inference from external lockfiles (e.g. ~/yarn.lock).
    // From apps/web, repo root is two levels up.
    outputFileTracingRoot: path.resolve(__dirname, '../..'),

    // Explicitly tell webpack what "@" resolves to.
    // Without this, Next.js can infer the wrong workspace root in CI
    // (e.g. when a stray yarn.lock exists in the runner's home dir),
    // causing all @/* imports to fail during the production build.
    webpack: (config) => {
        config.resolve.alias['@'] = path.resolve(__dirname);
        return config;
    },
};

export default withNextIntl(nextConfig);

