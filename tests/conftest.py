"""Test configuration: always use a throwaway SQLite database.

DATABASE_URL (e.g. a real Neon URL from .env) is deliberately overridden so the
tests, which clear the claims table, can never touch production data. Set
DATABASE_URL_TEST to run the suite against a dedicated PostgreSQL test database.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="claimguard_test_")
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL_TEST") or f"sqlite:///{_tmp}/test.db"

from app.database import init_db  # noqa: E402  (import after env is set)

init_db()
