import { getRequestConfig } from 'next-intl/server';
import { notFound } from 'next/navigation';

// Can be imported from a shared config
const locales = ['en', 'am'];

export default getRequestConfig(async ({ requestLocale }) => {
    // Await the locale for Next.js 15 compatibility
    const locale = await requestLocale;

    // Validate that the incoming `locale` parameter is valid
    if (!locale || !locales.includes(locale)) notFound();

    return {
        locale,
        messages: (await import(`../messages/${locale}.json`)).default,
    };
});
