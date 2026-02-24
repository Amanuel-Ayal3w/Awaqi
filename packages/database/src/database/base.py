"""
Shared declarative base for all SQLAlchemy ORM models.
Import Base from here in every model file to ensure they share
the same metadata object (required for Alembic auto-detection).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide declarative base."""
    pass
