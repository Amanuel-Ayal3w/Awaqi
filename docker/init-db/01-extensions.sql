-- Runs once on first container start (empty data volume).
-- Alembic migrations also enable these; this helps manual psql before migrate.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
