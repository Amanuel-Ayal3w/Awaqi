.PHONY: help check build-web test test-unit test-integration lint-py dev test-db

# --- Colors ---
GREEN  := \033[0;32m
RED    := \033[0;31m
CYAN   := \033[0;36m
BOLD   := \033[1m
RESET  := \033[0m
LINE   := -------------------------------------------------------

help:
	@echo ""
	@echo "$(BOLD)Available commands:$(RESET)"
	@echo "$(LINE)"
	@echo "  $(CYAN)make check$(RESET)             Run all CI checks (mirrors GitHub Actions)"
	@echo "  $(CYAN)make test$(RESET)              Run all Python tests (unit + integration)"
	@echo "  $(CYAN)make test-unit$(RESET)          Run only unit tests (no DB needed)"
	@echo "  $(CYAN)make test-integration$(RESET)   Run only integration tests (needs PostgreSQL)"
	@echo "  $(CYAN)make lint-py$(RESET)            Ruff lint check"
	@echo "  $(CYAN)make dev$(RESET)                Start backend + frontend (local dev)"
	@echo "  $(CYAN)make build-web$(RESET)          Lint, type-check, and build Next.js"
	@echo "$(LINE)"
	@echo ""

# --- Local dev (backend + frontend) -----------------------------------------
dev:
	@echo ""
	@echo "$(LINE)"
	@echo "$(BOLD)  STARTING DEV SERVERS$(RESET)"
	@echo "$(LINE)"
	@echo "  $(CYAN)Backend$(RESET)   http://localhost:8000"
	@echo "  $(CYAN)Frontend$(RESET)  http://localhost:3000"
	@echo "$(LINE)"
	@set -a && [ -f .env ] && . ./.env; set +a; \
		trap 'kill 0' INT TERM; \
		uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000 & \
		cd apps/web && npm run dev & \
		wait

# --- Run everything ---------------------------------------------------------
check: lint-py test build-web
	@echo ""
	@echo "$(LINE)"
	@echo "$(GREEN)$(BOLD)  ALL CHECKS PASSED -- safe to push$(RESET)"
	@echo "$(LINE)"
	@echo ""

# --- Python linting ---------------------------------------------------------
lint-py:
	@echo ""
	@echo "$(LINE)"
	@echo "$(BOLD)  RUFF LINT$(RESET)"
	@echo "$(LINE)"
	@uv run ruff check . \
		&& echo "$(GREEN)--- PASS: ruff lint$(RESET)" \
		|| (echo "$(RED)--- FAIL: ruff lint$(RESET)" && exit 1)

# --- Ensure test database exists --------------------------------------------
test-db:
	@PGPASSWORD=postgres psql -U postgres -h localhost -tc \
		"SELECT 1 FROM pg_database WHERE datname = 'awaqi_db_test'" | grep -q 1 \
		|| (echo "$(CYAN)Creating awaqi_db_test database...$(RESET)" && \
			PGPASSWORD=postgres createdb -U postgres -h localhost awaqi_db_test)

# --- Python tests (full suite) ----------------------------------------------
test: test-db
	@echo ""
	@echo "$(LINE)"
	@echo "$(BOLD)  PYTHON TESTS (all)$(RESET)"
	@echo "$(LINE)"
	@uv run --package api pytest tests/ -v --tb=short \
		&& echo "" && echo "$(GREEN)--- PASS: all python tests$(RESET)" \
		|| (echo "" && echo "$(RED)--- FAIL: python tests -- see errors above$(RESET)" && exit 1)

# --- Unit tests only (no DB required) ---------------------------------------
test-unit:
	@echo ""
	@echo "$(LINE)"
	@echo "$(BOLD)  UNIT TESTS (no DB needed)$(RESET)"
	@echo "$(LINE)"
	@uv run --package api pytest tests/api/test_schemas.py tests/api/test_session_token.py tests/packages/ -v --tb=short \
		&& echo "" && echo "$(GREEN)--- PASS: unit tests$(RESET)" \
		|| (echo "" && echo "$(RED)--- FAIL: unit tests -- see errors above$(RESET)" && exit 1)

# --- Integration tests only (needs PostgreSQL) ------------------------------
test-integration: test-db
	@echo ""
	@echo "$(LINE)"
	@echo "$(BOLD)  INTEGRATION TESTS (needs PostgreSQL)$(RESET)"
	@echo "$(LINE)"
	@uv run --package api pytest tests/api/test_health.py tests/api/test_chat_endpoints.py tests/api/test_admin_endpoints.py -v --tb=short \
		&& echo "" && echo "$(GREEN)--- PASS: integration tests$(RESET)" \
		|| (echo "" && echo "$(RED)--- FAIL: integration tests -- see errors above$(RESET)" && exit 1)

# --- Next.js Frontend -------------------------------------------------------
build-web: export BETTER_AUTH_SECRET ?= $(shell openssl rand -base64 32)
build-web: export DATABASE_URL_SYNC ?= postgresql://postgres:postgres@localhost:5432/awaqi_db
build-web: export NEXT_PUBLIC_APP_URL ?= http://localhost:3000
build-web: export NEXT_PUBLIC_API_URL ?= http://localhost:8000
build-web:
	@echo ""
	@echo "$(LINE)"
	@echo "$(BOLD)  BUILD WEB (Next.js)$(RESET)"
	@echo "$(LINE)"
	@cd apps/web && npm run build \
		&& echo "" && echo "$(GREEN)--- PASS: next.js build$(RESET)" \
		|| (echo "" && echo "$(RED)--- FAIL: next.js build -- see errors above$(RESET)" && exit 1)
