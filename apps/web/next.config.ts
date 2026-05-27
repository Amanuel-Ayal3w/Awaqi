import type { NextConfig } from 'next';
import { loadEnvConfig } from '@next/env';
import createNextIntlPlugin from 'next-intl/plugin';
import path from 'path';

// Next.js 15 does not support `envDir` on NextConfig. Mirror the old behavior by loading
// `.env*` from the monorepo root first, then apps/web (local overrides).
const repoRoot = path.resolve(__dirname, '../..');
loadEnvConfig(repoRoot);
loadEnvConfig(__dirname);

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const nextConfig: NextConfig = {
    // Produce a standalone build for Docker (copies all needed node_modules into .next/standalone)
    output: 'standalone',

    outputFileTracingRoot: path.resolve(__dirname, '../..'),

    webpack: (config) => {
        config.resolve.alias['@'] = path.resolve(__dirname);
        return config;
    },
};

export default withNextIntl(nextConfig);

