# Atlas (backend)

Personal ops agent API — FastAPI, async SQLAlchemy, PostgreSQL + pgvector. See `Project and Plan.md` for the full roadmap.

## Prerequisites (Windows)

Install **Python 3.11+** (from [python.org](https://www.python.org/downloads/), not the Microsoft Store), **Poetry**, and **PostgreSQL with pgvector** (local Windows install per `docs/setup_windows.md`, or a hosted provider such as **[Neon](https://neon.tech)** with pgvector). **GNU make is optional** — everything below uses `poetry run`.

For Neon, use a connection string with **`postgresql+asyncpg://`** and **`sslmode=require`** (or your dashboard’s async URL). Create the extension once: `psql "<postgres-url>" -c "CREATE EXTENSION IF NOT EXISTS vector;"` then `poetry run alembic upgrade head`.

### Create Postgres objects (once)

Run as the **`postgres`** superuser (PowerShell). Replace `YOUR_POSTGRES_PASSWORD` with the password you set for `postgres` during installation:

```powershell
$env:PGPASSWORD = "YOUR_POSTGRES_PASSWORD"
psql -U postgres -h localhost -c "CREATE USER atlas WITH PASSWORD 'atlas_dev';"
psql -U postgres -h localhost -c "CREATE DATABASE atlas_dev OWNER atlas;"
psql -U postgres -h localhost -c "CREATE DATABASE atlas_test OWNER atlas;"
psql -U postgres -h localhost -d atlas_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -h localhost -d atlas_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If `CREATE USER` fails because `atlas` already exists, skip that line. If `psql` is not on `PATH`, call it with the full path, for example `"C:\Program Files\PostgreSQL\16\bin\psql.exe"`.

## Quickstart

From this directory:

```powershell
poetry install
poetry run pre-commit install
Copy-Item .env.example .env
# Edit .env if your password or host differs.
poetry run alembic upgrade head
poetry run uvicorn atlas.main:app --reload --host 0.0.0.0 --port 8000
```

Then:

```powershell
curl http://localhost:8000/health
```

You should see `{"status":"ok","db":"ok"}` when Postgres is reachable.

## Quality gate (no Make)

```powershell
poetry run ruff check src tests
poetry run ruff format --check src tests
poetry run mypy src tests
poetry run pytest -q
```

## Reset dev database (optional)

Set `ATLAS_ADMIN_DATABASE_URL` in `.env` (superuser URL on the `postgres` database), then:

```powershell
poetry run python scripts/reset_db.py
```

## Layout

Application code lives under `src/atlas/` per the phase-1 plan (`api/`, `db/`, `models/`, …).
