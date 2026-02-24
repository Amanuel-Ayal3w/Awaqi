.PHONY: help check build-web

# Default: show available commands
help:
	@echo ""
	@echo "  make check      → Run all CI checks (mirrors GitHub Actions)"
	@echo "  make build-web  → Lint, type-check, and build Next.js"
	@echo ""

# ──────────────────────────────────────────────
# Run everything — mirrors what GitHub Actions does
# ──────────────────────────────────────────────
check: build-web
	@echo ""
	@echo "✅ All checks passed! Safe to push."

# ──────────────────────────────────────────────
# Next.js Frontend — lint + type-check + build
# ──────────────────────────────────────────────
build-web:
	@echo "�  Building Next.js (includes TypeScript check)..."
	cd apps/web && npm run build
