# Windows development setup (Atlas)

This guide matches **Phase 1** in `Project and Plan.md`: native Windows Python + Poetry + PostgreSQL 16 + pgvector, no Docker.

## 1. Python 3.11

1. Download the Windows installer from [python.org/downloads](https://www.python.org/downloads/windows/).
2. During setup, enable **“Add python.exe to PATH”**.
3. Avoid the Microsoft Store build for this project (PATH / permission quirks are common).
4. Verify in a **new** PowerShell window:

```powershell
python --version
```

Expect `Python 3.11.x`.

## 2. Poetry

In PowerShell:

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Add Poetry to PATH if the installer says so, then reopen the shell and run:

```powershell
poetry --version
```

## 3. PostgreSQL 16 (EDB installer)

1. Install from EnterpriseDB’s Windows builds (PostgreSQL 16.x).
2. Remember the **`postgres` superuser password** — you need it for admin tasks and optional `ATLAS_ADMIN_DATABASE_URL`.
3. Optionally install pgAdmin from the same wizard.

## 4. pgvector (extension) — version **v0.7.4**

Atlas records this version in the plan; keep it aligned with what you compile.

1. Install **Visual Studio Build Tools** with the **“Desktop development with C++”** workload (MSVC + Windows SDK).
2. Open **“x64 Native Tools Command Prompt for VS”** as **Administrator**.
3. Set `PGROOT` to your PostgreSQL root, for example:

   ```bat
   set "PGROOT=C:\Program Files\PostgreSQL\16"
   ```

4. Build and install pgvector:

   ```bat
   git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
   cd pgvector
   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```

5. In pgAdmin (or `psql`), connect to any database and run:

   ```sql
   CREATE EXTENSION vector;
   ```

   If this succeeds, the extension is installed correctly.

### Common pgvector pitfalls

- Building from a normal PowerShell without MSVC in PATH usually fails — use the **Native Tools** prompt.
- `PGROOT` must match the instance you use in PATH (`pg_config` should resolve under that tree).
- Mixing 32-bit and 64-bit toolchains causes confusing linker errors — stay on **x64**.

## 5. GNU `make`

The Makefile targets (`make dev`, `make check`, …) expect **GNU make**.

- **Chocolatey:** `choco install make` (run shell as Administrator).
- **Scoop:** install `gnumake` and ensure `make.exe` is on PATH.

Verify:

```powershell
make --version
```

If you cannot install `make`, run the equivalent `poetry run …` commands from `Makefile` manually.

## 6. Databases and roles

Using pgAdmin or `psql` as `postgres`:

```sql
CREATE USER atlas WITH PASSWORD 'atlas_dev';
CREATE DATABASE atlas_dev OWNER atlas;
CREATE DATABASE atlas_test OWNER atlas;
\c atlas_dev
CREATE EXTENSION vector;
\c atlas_test
CREATE EXTENSION vector;
```

If you pick a different password, update `DATABASE_URL` / `TEST_DATABASE_URL` in `.env`.

## 7. Project install

In the repo root:

```powershell
poetry install
poetry run pre-commit install
Copy-Item .env.example .env
```

Edit `.env` if needed, then:

```powershell
poetry run alembic upgrade head
poetry run uvicorn atlas.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```powershell
curl http://localhost:8000/health
```

## 8. PowerShell notes

- If running local scripts is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Prefer **new terminals** after changing PATH so `python`, `poetry`, `psql`, and `make` resolve consistently.

## 9. Optional: `make reset-db`

Add a superuser URL to `.env`:

```env
ATLAS_ADMIN_DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SUPERUSER_PASSWORD@localhost:5432/postgres
```

Then `make reset-db` can drop/recreate the DB named in `DATABASE_URL` and re-run Alembic. Omit this if you prefer to manage databases only in pgAdmin.
