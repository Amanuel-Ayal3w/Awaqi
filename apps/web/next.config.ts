import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';
import path from 'path';

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

