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
	@echo "🔍 Type-checking and building Next.js..."
	cd apps/web && npm run type-check && npm run build
