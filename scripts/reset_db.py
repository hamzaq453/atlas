"""Drop and recreate the dev database, then run Alembic migrations.

Requires `ATLAS_ADMIN_DATABASE_URL` in `.env` (superuser, database `postgres`).
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path

import asyncpg
from sqlalchemy.engine.url import make_url

from atlas.config import get_settings

ROOT_DIR = Path(__file__).resolve().parents[1]
IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _to_asyncpg_dsn(url: str) -> str:
    parsed = make_url(url)
    return parsed.set(drivername="postgresql").render_as_string(hide_password=False)


def _require_safe_ident(name: str | None, label: str) -> str:
    if not name or not IDENT_RE.match(name):
        msg = f"Unsafe or missing {label} identifier parsed from DATABASE_URL"
        raise SystemExit(msg)
    return name


async def _reset() -> None:
    settings = get_settings()
    if not settings.atlas_admin_database_url:
        print(  # noqa: T201
            "ATLAS_ADMIN_DATABASE_URL is not set. Add a superuser URL to `.env`, e.g.\n"
            "ATLAS_ADMIN_DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/postgres\n"
            "Then rerun: poetry run python scripts/reset_db.py (or `make reset-db`).",
        )
        raise SystemExit(1)

    target = make_url(settings.database_url)
    db_name = _require_safe_ident(target.database, "database")
    owner = _require_safe_ident(target.username, "owner")

    admin_dsn = _to_asyncpg_dsn(settings.atlas_admin_database_url)

    conn = await asyncpg.connect(admin_dsn)
    try:
        rows = await conn.fetch(
            "SELECT pid FROM pg_stat_activity WHERE datname = $1",
            db_name,
        )
        for row in rows:
            await conn.execute("SELECT pg_terminate_backend($1)", row["pid"])

        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}" OWNER "{owner}"')
    finally:
        await conn.close()

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT_DIR,
        check=True,
    )


def main() -> None:
    asyncio.run(_reset())
    print("reset-db: complete")  # noqa: T201


if __name__ == "__main__":
    main()
