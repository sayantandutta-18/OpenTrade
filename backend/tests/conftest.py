"""Pytest fixtures for ImpactLab tests."""

from __future__ import annotations

import pytest

from impactlab.db.session import init_db


@pytest.fixture(autouse=True)
def setup_database() -> None:
    """Ensure database tables exist before each test."""
    init_db()
