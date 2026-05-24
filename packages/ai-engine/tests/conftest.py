"""Pytest defaults so importing ai_engine modules that pull in ``database`` does not fail."""

from __future__ import annotations

import os

# Lazy-connect packages only need a syntactically valid URL at import time for some paths.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/awaqi_db_test",
)
