import { describe, expect, it } from 'vitest';

import { adminDocumentReviewPath, adminReviewBackPath } from './admin-routes';

describe('adminDocumentReviewPath', () => {
    it('builds review URL with default from=documents', () => {
        expect(adminDocumentReviewPath('en', 'doc-1')).toBe(
            '/en/admin/documents/doc-1/review?from=documents',
        );
    });

    it('includes custom from query param', () => {
        expect(adminDocumentReviewPath('am', 'doc-2', 'scraper')).toBe(
            '/am/admin/documents/doc-2/review?from=scraper',
        );
    });
});

describe('adminReviewBackPath', () => {
    it('returns scraper path when from=scraper', () => {
        expect(adminReviewBackPath('en', 'scraper')).toBe('/en/admin/scraper');
    });

    it('returns review-queue path when from=review-queue', () => {
        expect(adminReviewBackPath('en', 'review-queue')).toBe('/en/admin/review-queue');
    });

    it('defaults to documents list', () => {
        expect(adminReviewBackPath('en', null)).toBe('/en/admin/documents');
        expect(adminReviewBackPath('en', 'documents')).toBe('/en/admin/documents');
    });
});
