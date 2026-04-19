# Atlas — Personal Ops Agent

> **Single source of truth.** This document is the authoritative plan for building Atlas. Cursor should treat this as the primary reference. Keep it updated: after finishing a task, change its checkbox from `[ ]` to `[x]` and add a short note under the phase's "Completion Log".

---

## 0. Project Overview

**What Atlas is.** A personal ops agent for Hamza — a chief-of-staff AI that reads Gmail, Google Calendar, and GitHub; maintains long-term semantic memory about his work and life; generates proactive daily briefings; and handles delegated tasks via a conversational interface. Backend-first build; Next.js frontend is a separate project built after the backend is functional.

**Core design principles.**
1. **Provider-agnostic.** LLM, embeddings, STT, and notification providers are behind interfaces. Start on Gemini free tier; swap to Claude/GPT later with one config change.
2. **Memory is the moat.** Atlas's value is that it knows Hamza. Invest in the memory subsystem early and properly.
3. **Multi-agent, pragmatic.** Planner/executor with specialist sub-agents per domain. No over-decomposition — tools stay shared.
4. **Start simple, add infra only when needed.** No Docker, no Redis, no message queues until there's a concrete problem they solve. Native Windows Postgres + Python is enough for the first 7 phases.
5. **Phase gates are hard gates.** Do not start phase N+1 until phase N's acceptance criteria are all green. No "I'll come back to it."

**Stack summary.**

| Layer | Choice |
|---|---|
| Runtime | Python 3.11+, Poetry |
| OS (dev) | Windows — native Postgres, native Python |
| Web framework | FastAPI + Uvicorn, SSE streaming |
| Agent orchestration | LangGraph + LangChain (tool abstractions only) |
| LLM (default) | Gemini 2.5 Flash / Pro via `google-generativeai` |
| Embeddings | Gemini `text-embedding-004` (768-dim) |
| Database | PostgreSQL 16 + pgvector (native Windows install), SQLAlchemy 2.0 async, Alembic |
| Cache/pubsub | None in phases 1–7. Postgres LISTEN/NOTIFY or Redis added in phase 8 if needed. |
| Scheduler | APScheduler (async, in-process, Postgres jobstore) |
| STT | Deepgram (phase 10) |
| Auth | OAuth2 (Google), PAT (GitHub), internal JWT (single user) |
| Observability | LangSmith (free tier) + structlog |
| Testing | pytest, pytest-asyncio, httpx, factory-boy |
| Quality | Ruff, mypy (strict), pre-commit |
| Deployment | EC2 + systemd + Python venv (phase 12). Docker optional. |

---

## 1. How To Use This Document (for Cursor and for Hamza)

**Before starting any task:**
1. Read the current phase's overview and task list.
2. Read the "Acceptance Criteria" for the phase — that's the bar.
3. Check the "Completion Log" to understand what's already done.

**While working on a task:**
- Follow the file structure laid out in Phase 1. Don't reinvent the layout.
- Every new module gets a test file. No untested code merged into a phase.
- Run `make check` (defined in phase 1) before marking a task complete.

**After finishing a task:**
1. Flip its checkbox in this file from `[ ]` to `[x]`.
2. Add a one-line note to the phase's Completion Log with date and commit SHA.
3. If you discovered something that changes future phases, add a note under "Decisions & Deviations" at the bottom.

**Before moving to the next phase:**
- All checkboxes for the current phase must be `[x]`.
- All acceptance criteria must pass.
- Run the phase's "Phase Gate Check" command — it must exit 0.

---

## 2. Architecture At A Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Layer                            │
│    /chat (SSE)   /tasks   /memory   /admin   /transcribe        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    LangGraph Orchestrator                        │
│                                                                  │
│   ┌─────────┐    ┌──────────────────────────────────────────┐  │
│   │ Planner │──▶│  Router: simple tool call | multi-step   │  │
│   └─────────┘    └──────────┬───────────────────────────────┘  │
│                             │                                    │
│         ┌───────────┬───────┼───────┬───────────┬────────────┐ │
│         ▼           ▼       ▼       ▼           ▼            ▼ │
│    ┌────────┐  ┌────────┐ ┌───┐ ┌──────┐  ┌─────────┐  ┌───┐ │
│    │ Email  │  │Calendar│ │Git│ │Memory│  │Briefing │  │...│ │
│    │ Agent  │  │ Agent  │ │Hub│ │Agent │  │ Agent   │  │   │ │
│    └───┬────┘  └───┬────┘ └─┬─┘ └──┬───┘  └────┬────┘  └───┘ │
│        │           │        │      │           │                │
│        └───────────┴────────┴──────┴───────────┘                │
│                             │                                    │
│                   ┌─────────▼──────────┐                        │
│                   │   Shared Tools     │                        │
│                   │  (HTTP, DB, RAG)   │                        │
│                   └─────────┬──────────┘                        │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  Postgres + pgvector (native)  │   External APIs                │
│  ─ conversations               │  ─ Gmail                        │
│  ─ messages                    │  ─ Calendar                     │
│  ─ facts                       │  ─ GitHub                       │
│  ─ entities                    │  ─ Deepgram (p10)               │
│  ─ episodes (vector)           │  ─ Gemini                       │
│  ─ tasks                       │                                 │
│  ─ integrations                │                                 │
│  ─ apscheduler_jobs            │                                 │
└─────────────────────────────────────────────────────────────────┘

Background workers (APScheduler, in-process):
  ─ Gmail sync       (every 5 min)
  ─ Calendar sync    (every 15 min)
  ─ GitHub sync      (every 10 min)
  ─ Morning briefing (8am Asia/Karachi)
  ─ Memory consolidation (nightly)
  ─ Event triggers   (reactive, via in-process event bus or Postgres LISTEN/NOTIFY)
```

---

## 3. Phases (Execution Order)

Each phase has a clear deliverable. Do not skip. Do not parallelize across phases.

| # | Phase | Deliverable | Est. Effort |
|---|---|---|---|
| 1 | Project Bootstrap (Windows-native) | Running FastAPI app, DB, migrations, CI quality gates | 1 day |
| 2 | LLM Provider Layer + Basic Chat | Streaming chat endpoint using Gemini, provider-swappable | 1-2 days |
| 3 | Memory Foundation | Facts, entities, episodes, embeddings, hybrid retrieval | 3-5 days |
| 4 | Agent Core (LangGraph) | Orchestrator + first specialist (Memory Agent) working end-to-end | 2-3 days |
| 5 | Gmail Integration | OAuth, sync, EmailAgent, tools, tests | 3-4 days |
| 6 | Calendar Integration | OAuth (shared), sync, CalendarAgent, tools | 2 days |
| 7 | GitHub Integration | PAT, sync, CodeAgent, tools | 2-3 days |
| 8 | Proactive Layer | Scheduler, morning briefing, event triggers, notification bus | 3 days |
| 9 | Task/Delegation System | Long-running task executor, history, status | 2 days |
| 10 | Voice Input | `/transcribe` endpoint with Deepgram | 0.5 day |
| 11 | Observability + Eval Harness | LangSmith wired, eval suite, admin endpoints | 1-2 days |
| 12 | Hardening + Deployment | EC2 deploy, production configs, monitoring | 2-3 days |

---

## 4. PHASE 1 — Project Bootstrap (Windows-Native)

**Goal.** A running FastAPI app connected to a native Windows Postgres (with pgvector) via Poetry, with migrations, tests, linting, and a `make check` gate that enforces quality before any feature code ships. No Docker, no Redis.

### Pre-flight (one-time, outside the repo)

- [ ] **1.0.1** Install Python 3.11 from python.org (not the Microsoft Store version — it has path issues). Verify `python --version` is 3.11.x.
- [ ] **1.0.2** Install Poetry: `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -`. Add Poetry to PATH. Verify `poetry --version`.
- [ ] **1.0.3** Install PostgreSQL 16 for Windows (via the EDB installer). Keep pgAdmin. Note the superuser password.
- [ ] **1.0.4** **Install pgvector on Windows Postgres.** This is the one non-trivial step:
  - Install Visual Studio Build Tools (C++ workload) if not already installed.
  - Open "x64 Native Tools Command Prompt for VS" as Administrator.
  - Set `PGROOT` to your Postgres install dir (e.g., `set "PGROOT=C:\Program Files\PostgreSQL\16"`).
  - `git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git`
  - `cd pgvector`
  - `nmake /F Makefile.win`
  - `nmake /F Makefile.win install`
  - Verify in pgAdmin: connect to a DB, run `CREATE EXTENSION vector;` — should succeed.
  - Document the exact version installed in `docs/setup_windows.md`.
- [ ] **1.0.5** Install `make` on Windows. Easiest: `choco install make` (via Chocolatey) or use `gnumake` via scoop. Alternatively, write tasks as `.ps1` scripts and call them via `poetry run`. Plan assumes `make` is available.
- [ ] **1.0.6** Create the dev database and user via pgAdmin or psql:
  ```sql
  CREATE USER atlas WITH PASSWORD 'atlas_dev';
  CREATE DATABASE atlas_dev OWNER atlas;
  CREATE DATABASE atlas_test OWNER atlas;
  \c atlas_dev
  CREATE EXTENSION vector;
  \c atlas_test
  CREATE EXTENSION vector;
  ```

### Tasks

- [ ] **1.1** Initialize repo with Poetry. `pyproject.toml` with Python 3.11+, dependencies: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sqlalchemy[asyncio]>=2`, `asyncpg`, `alembic`, `structlog`, `python-dotenv`. Dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit`, `factory-boy`. **No `redis` package.**
- [ ] **1.2** Create project layout:
  ```
  atlas/
  ├── pyproject.toml
  ├── .env.example
  ├── Makefile
  ├── alembic.ini
  ├── migrations/
  ├── docs/
  │   └── setup_windows.md
  ├── src/
  │   └── atlas/
  │       ├── __init__.py
  │       ├── main.py                 # FastAPI app factory
  │       ├── config.py               # Pydantic settings
  │       ├── logging.py              # structlog setup
  │       ├── db/
  │       │   ├── __init__.py
  │       │   ├── session.py          # async engine + sessionmaker
  │       │   └── base.py             # Declarative base
  │       ├── models/                 # SQLAlchemy models (filled in later phases)
  │       ├── schemas/                # Pydantic DTOs
  │       ├── api/
  │       │   ├── __init__.py
  │       │   ├── deps.py             # shared FastAPI deps
  │       │   └── routes/
  │       │       └── health.py
  │       ├── services/               # business logic (filled later)
  │       ├── agents/                 # LangGraph stuff (phase 4+)
  │       ├── integrations/           # Gmail/Calendar/GitHub (phase 5+)
  │       ├── workers/                # APScheduler jobs (phase 8)
  │       └── utils/
  └── tests/
      ├── conftest.py
      ├── unit/
      └── integration/
  ```
- [ ] **1.3** `config.py` with `Settings(BaseSettings)` — reads from `.env`. Fields: `DATABASE_URL`, `TEST_DATABASE_URL`, `GEMINI_API_KEY`, `LLM_PROVIDER` (default `gemini`), `LOG_LEVEL`, `ENV` (local/prod), `TIMEZONE` (default `Asia/Karachi`). **No Redis URL.**
- [ ] **1.4** `.env.example` with all variables documented. Example `DATABASE_URL`: `postgresql+asyncpg://atlas:atlas_dev@localhost:5432/atlas_dev`. Real `.env` is gitignored.
- [ ] **1.5** Alembic initialized, pointed at the async engine. First migration: `CREATE EXTENSION IF NOT EXISTS vector;` (idempotent — safe if already created manually).
- [ ] **1.6** `db/session.py` — async engine factory, `get_db` dependency for FastAPI.
- [ ] **1.7** `logging.py` — structlog configured for JSON output in prod, pretty console in local.
- [ ] **1.8** `main.py` — FastAPI app factory, CORS for `localhost:3000` (Next.js), mounts `/health` route, sets up logging on startup.
- [ ] **1.9** `/health` endpoint — returns `{"status": "ok", "db": "ok"|"error"}` with an actual `SELECT 1` connectivity check. (No Redis check; removed.)
- [ ] **1.10** `Makefile` with targets: `install`, `dev` (uvicorn with reload), `migrate`, `migration name=X` (autogen), `test`, `lint` (ruff check + mypy), `format` (ruff format), `check` (lint + test), `reset-db` (drops and recreates dev DB, runs migrations). Note for Windows: Makefile recipes should work with GNU make; document any PowerShell quirks.
- [ ] **1.11** `pre-commit` config with ruff, ruff-format, and a check that no `print()` statements are committed.
- [ ] **1.12** Ruff config in `pyproject.toml`: line length 100, enable `E`, `F`, `I`, `N`, `UP`, `B`, `A`, `SIM`, `RUF`. Mypy strict mode, `ignore_missing_imports = false` with explicit excludes for third-party libs without stubs.
- [ ] **1.13** First unit test in `tests/unit/test_config.py` (settings load correctly) and first integration test in `tests/integration/test_health.py` (health endpoint returns 200, db check passes). `conftest.py` with async client fixture and DB transaction rollback fixture that uses `atlas_test` database.
- [ ] **1.14** README.md — quickstart targeted at Windows: install prereqs (see `docs/setup_windows.md`), `poetry install`, `cp .env.example .env` (or PowerShell `Copy-Item`), `make migrate`, `make dev`. Include screenshot-quality steps.
- [ ] **1.15** `docs/setup_windows.md` — detailed Windows setup guide covering: Python, Poetry, PostgreSQL, pgvector compile, make on Windows, common pitfalls (path issues, ExecutionPolicy for PowerShell scripts).

### Acceptance Criteria

1. Fresh clone → follow `docs/setup_windows.md` → `make install && make migrate && make dev` → server starts on :8000.
2. `curl localhost:8000/health` returns 200 with `db: ok`.
3. In pgAdmin, the `atlas_dev` database has all alembic migrations applied and `vector` extension active.
4. `make check` passes clean (ruff, mypy, pytest) with zero warnings.
5. Pre-commit hook blocks a commit containing `print("hi")`.
6. Can kill and restart `make dev` cleanly; no orphan processes, no port conflicts.

### Phase Gate Check

```bash
make reset-db && make migrate && make check
# Then in one terminal:
make dev
# In another:
curl -f localhost:8000/health
```

All commands exit 0, health endpoint returns JSON with `db: ok`.

### Completion Log
<!-- Add entries like: - 2026-04-20: Task 1.1 done, commit abc1234 -->

---

## 5. PHASE 2 — LLM Provider Layer + Basic Chat

**Goal.** A streaming `/chat` endpoint that talks to Gemini, with the provider behind an interface so Claude/GPT are drop-in replacements.

### Tasks

- [ ] **2.1** Define `LLMProvider` protocol in `services/llm/base.py`:
  - `async def complete(messages: list[Message], **opts) -> LLMResponse`
  - `async def stream(messages: list[Message], **opts) -> AsyncIterator[LLMChunk]`
  - `async def embed(texts: list[str]) -> list[list[float]]`
  - `name: str`, `model: str`, `max_context: int`
- [ ] **2.2** Pydantic types: `Message(role, content, tool_calls, tool_call_id)`, `LLMResponse(content, tool_calls, usage)`, `LLMChunk(delta, finish_reason, usage)`.
- [ ] **2.3** Implement `GeminiProvider` in `services/llm/gemini.py` using `google-generativeai`. Map our `Message` schema to/from Gemini's format. Handle tool calls via Gemini function calling. Implement `embed` using `text-embedding-004`.
- [ ] **2.4** Provider factory `services/llm/__init__.py::get_llm()` reads `LLM_PROVIDER` from settings and returns the right implementation. Register `gemini`; leave stubs for `claude` and `openai` raising `NotImplementedError`.
- [ ] **2.5** Conversation and message models in `models/conversation.py`:
  - `Conversation(id, user_id, title, created_at, updated_at)`
  - `ConversationMessage(id, conversation_id, role, content, tool_calls_json, created_at)`
- [ ] **2.6** Alembic migration for conversations/messages tables.
- [ ] **2.7** `POST /chat` endpoint — body: `{conversation_id?: UUID, message: str, stream: bool=true}`. If no `conversation_id`, create one. Persist user message, call LLM, persist assistant reply, return SSE stream (or JSON if `stream=false`).
- [ ] **2.8** SSE implementation: emit events `{type: "token", data: "..."}`, `{type: "done", conversation_id, message_id}`, `{type: "error", message}`. Proper content-type, heartbeat every 15s.
- [ ] **2.9** `GET /conversations` (list), `GET /conversations/{id}/messages` (history).
- [ ] **2.10** System prompt baseline in `services/prompts/system.py` — placeholder that will be enriched with memory context in phase 3.
- [ ] **2.11** Token counting utility — approximate for now (1 token ≈ 4 chars for Gemini), refine later. Enforce max-context by truncating old messages.
- [ ] **2.12** Unit tests: GeminiProvider with mocked HTTP, factory returns correct provider, message serialization roundtrip.
- [ ] **2.13** Integration test: POST to `/chat`, assert SSE stream arrives, conversation + messages persisted.
- [ ] **2.14** CLI smoke test script `scripts/chat_cli.py` — interactive REPL that hits `/chat` and prints stream. For manual testing.

### Acceptance Criteria

1. `python scripts/chat_cli.py` → type "hi" → get a streamed reply from Gemini.
2. Conversation and messages appear in DB with correct FK links.
3. `GET /conversations/{id}/messages` returns the full history in order.
4. Swapping `LLM_PROVIDER=claude` in `.env` raises a clear `NotImplementedError` at startup (proves the factory is wired).
5. All unit and integration tests pass, `make check` clean.

### Phase Gate Check

```bash
make check && python scripts/chat_cli.py --once "say hello"
```

### Completion Log

---

## 6. PHASE 3 — Memory Foundation

**Goal.** Atlas has semantic memory: it stores facts, entities, and episodes, retrieves them by hybrid search, and injects relevant ones into every LLM call. This is the highest-leverage phase — don't rush it.

### Tasks

- [ ] **3.1** Schema design in `models/memory.py`:
  - `Entity(id, type, canonical_name, aliases_json, attributes_json, created_at, updated_at)` — types: `person`, `project`, `company`, `repo`, `topic`
  - `EntityRelation(id, from_entity_id, to_entity_id, relation_type, attributes_json, created_at)` — e.g., "works_at", "member_of", "assigned_to"
  - `Fact(id, subject_entity_id, predicate, object_value, object_entity_id?, confidence, source_type, source_ref, created_at, superseded_at?, superseded_by_fact_id?)` — e.g., `subject=Hamza, predicate="works_at", object_entity=Evren AI`
  - `Episode(id, conversation_id?, content, embedding vector(768), metadata_json, created_at)` — a compressed record of an interaction or external event
  - Indexes: HNSW on `episode.embedding`, GIN on entity aliases, btree on fact (subject, predicate).
- [ ] **3.2** Alembic migration. Verify HNSW index creation succeeds.
- [ ] **3.3** `services/memory/entities.py`:
  - `upsert_entity(type, canonical_name, aliases, attributes) -> Entity` with alias-based dedup
  - `find_entity(query: str) -> Entity | None` — fuzzy match on name + aliases
  - `link_entities(from_id, to_id, relation, attrs)`
- [ ] **3.4** `services/memory/facts.py`:
  - `write_fact(subject, predicate, object, confidence, source)` — if a non-contradicting fact with same (subject, predicate) exists, update confidence; if contradicting, mark old as superseded
  - `get_facts_about(entity_id, predicates?) -> list[Fact]`
  - `search_facts(query: str) -> list[Fact]` — simple text search for v1
- [ ] **3.5** `services/memory/episodes.py`:
  - `write_episode(content, metadata, conversation_id?) -> Episode` — embeds via LLMProvider, stores
  - `search_episodes(query: str, k=10, filter_metadata?) -> list[Episode]` — vector similarity with optional metadata filter
- [ ] **3.6** Hybrid retriever `services/memory/retriever.py`:
  - `retrieve(query, k=15) -> MemoryContext` where `MemoryContext = { facts: [...], entities: [...], episodes: [...] }`
  - Combines: entity extraction from query → related facts, vector search over episodes, keyword search over facts. Deduplicates and ranks.
- [ ] **3.7** Memory extractor `services/memory/extractor.py`:
  - `extract_from_conversation(messages) -> ExtractionResult` — LLM call with structured output (Pydantic schema) that returns new facts, new/updated entities, and one episode summary
  - Uses a dedicated system prompt focused on extraction
  - Confidence scoring: LLM must emit 0.0-1.0 for each fact
- [ ] **3.8** Background consolidation worker (wired into phase 8's scheduler, but class defined now): `services/memory/consolidator.py` with `run_consolidation()` that runs the extractor over recent conversations and writes results.
- [ ] **3.9** Inject memory into chat: update `/chat` endpoint to call `retriever.retrieve(user_message)` before sending to LLM, format `MemoryContext` into the system prompt.
- [ ] **3.10** Prompt template in `services/prompts/memory.py` — clean formatting of facts/entities/episodes into the system message. Budget-aware (don't blow the context window).
- [ ] **3.11** `/memory` admin routes:
  - `GET /memory/entities?q=...` — search entities
  - `GET /memory/facts?subject=...` — facts about an entity
  - `POST /memory/facts` — manually add a fact (for seeding)
  - `GET /memory/episodes?q=...` — search episodes
  - `DELETE /memory/episodes/{id}` — for correcting bad memories
- [ ] **3.12** Seed script `scripts/seed_memory.py` — loads Hamza's baseline facts (name, employer, stack, projects, key people like Karsan/John/Isha, FYP details). Run once after first migration.
- [ ] **3.13** Unit tests for each memory service. Integration test: chat, extract, verify facts persisted, next chat retrieves them.
- [ ] **3.14** Eval: ask "who do I work with at Evren?" — after seeding, it should mention Karsan and Isha from retrieved facts, not hallucinate.

### Acceptance Criteria

1. Seed script runs, `GET /memory/entities?q=evren` returns Evren AI entity with correct attributes.
2. Chat about a new topic ("I'm starting to learn Rust") → run consolidator → `GET /memory/facts?subject={hamza_id}` includes a fact like `(hamza, learning, rust, 0.8)`.
3. Later chat "what am I learning?" — response mentions Rust, not from model training but from retrieved memory (verify via LangSmith trace).
4. Hybrid retriever returns results mixing facts + episodes for relevant queries; returns empty for irrelevant queries.
5. HNSW index is used (check `EXPLAIN` on a vector query).
6. All tests pass, `make check` clean.

### Phase Gate Check

```bash
make check && \
python scripts/seed_memory.py && \
python scripts/memory_eval.py  # written as part of 3.14
```

### Completion Log

---

## 7. PHASE 4 — Agent Core (LangGraph)

**Goal.** Replace the direct LLM call in `/chat` with a LangGraph orchestrator that routes to specialist agents. First specialist wired in: **MemoryAgent**. Gmail/Calendar/GitHub agents come in their own phases.

### Tasks

- [ ] **4.1** Graph state schema in `agents/state.py` (TypedDict): `user_message`, `conversation_id`, `plan`, `memory_context`, `agent_trace`, `tool_results`, `final_response`.
- [ ] **4.2** Orchestrator graph in `agents/orchestrator.py`:
  - Node: `retrieve_memory` (calls phase 3 retriever)
  - Node: `plan` (LLM call — decides: direct_reply | call_specialist | multi_step)
  - Conditional edge: route to `direct_reply`, `memory_agent`, or `multi_step_executor`
  - Node: `direct_reply` (simple LLM call with memory context)
  - Node: `multi_step_executor` (loops through plan steps, dispatching to specialists)
  - Node: `finalize` (composes final response from agent outputs)
  - Compile with checkpointing (postgres checkpoint saver from langgraph)
- [ ] **4.3** `agents/base.py` — `SpecialistAgent` abstract class with `name`, `description`, `tools`, and `async def run(state, inputs) -> AgentOutput`.
- [ ] **4.4** Shared tool layer `agents/tools/`:
  - `memory_tools.py` — `search_memory`, `write_fact`, `search_episodes`
  - `time_tools.py` — `now`, `today`, `parse_natural_date` (for "next tuesday")
  - Tool registry pattern: each tool is a LangChain `Tool` with Pydantic input schema
- [ ] **4.5** `MemoryAgent` in `agents/specialists/memory_agent.py` — handles "what do you know about X", "remember that...", "forget that...", "correct: actually X is Y". Uses memory tools; can write new facts on the user's instruction.
- [ ] **4.6** Planner prompt in `services/prompts/planner.py` — teaches the LLM the routing taxonomy and specialist descriptions. Emits structured output: `{action, specialist?, steps?, direct_reply?}`.
- [ ] **4.7** Update `/chat` endpoint — invoke orchestrator graph, stream tokens from the final node.
- [ ] **4.8** Tracing: every node emits structured log with `conversation_id`, `node`, `duration_ms`, `input_summary`, `output_summary`. Foundation for phase 11 LangSmith wiring.
- [ ] **4.9** Error handling: node failures produce a graceful "I couldn't do that because..." response; full error stays in logs.
- [ ] **4.10** Tests: graph compiles, routes simple greeting to `direct_reply`, routes "what do you remember about Karsan" to `MemoryAgent`, fallback on planner failure.

### Acceptance Criteria

1. `/chat` with "hi" → planner picks `direct_reply`, normal response.
2. `/chat` with "remember that I prefer pnpm over npm" → MemoryAgent writes a fact.
3. `/chat` with "what do you remember about my stack preferences" → response cites the pnpm fact.
4. Graph execution traces are emitted for every request, visible in logs with proper structure.
5. Checkpointing works — interrupt a long-running graph invocation and resume via checkpoint ID.
6. `make check` clean.

### Phase Gate Check

```bash
make check && python scripts/agent_smoke.py
```

### Completion Log

---

## 8. PHASE 5 — Gmail Integration

**Goal.** Atlas can read, search, summarize, and draft emails via `EmailAgent`.

### Tasks

- [ ] **5.1** OAuth2 setup: register Google Cloud project, enable Gmail API, download client secrets. Scopes: `gmail.readonly`, `gmail.send`, `gmail.compose`. (Document steps in `docs/oauth_setup.md`.)
- [ ] **5.2** `Integration` model in `models/integration.py`: `(id, user_id, provider, access_token_encrypted, refresh_token_encrypted, scopes, metadata_json, expires_at, created_at)`. Encryption via Fernet, key from settings.
- [ ] **5.3** `integrations/google/oauth.py`: `build_auth_url(state) -> str`, `exchange_code(code) -> Tokens`, `refresh(integration) -> Tokens`. Auto-refresh before every API call if near expiry.
- [ ] **5.4** `POST /integrations/google/connect` — returns auth URL. `GET /integrations/google/callback` — exchanges code, persists tokens.
- [ ] **5.5** Gmail models: `EmailMessage(id, message_id, thread_id, from_addr, to_addrs, subject, body_text, body_html, snippet, labels, received_at, is_read, importance_score?, sender_tag?, embedding)`. Embedding of subject+snippet.
- [ ] **5.6** `integrations/google/gmail_sync.py::sync_recent(since)` — pulls messages since timestamp, upserts into DB, embeds new ones. Respects rate limits.
- [ ] **5.7** Sender classification in `services/email/classifier.py` — LLM-tags each new sender as `client | team | personal | noise | unknown`. Cached per sender (in DB, since there's no Redis). Updateable by user correction.
- [ ] **5.8** Importance scoring — heuristic v1: from a `client` or `team` sender + mentions Hamza's name/projects → high; from `noise` → low. LLM-refined later.
- [ ] **5.9** Email tools in `agents/tools/email_tools.py`:
  - `search_emails(query, from?, since?, limit=10)` — hybrid (vector + keyword + filters)
  - `read_thread(thread_id)`
  - `summarize_inbox(since, sender_tag_filter?)`
  - `draft_reply(thread_id, instructions)` — returns draft, does NOT send
  - `send_email(to, subject, body)` — only on explicit user confirmation (gated)
- [ ] **5.10** `EmailAgent` in `agents/specialists/email_agent.py` — registered with orchestrator, planner prompt updated to include it.
- [ ] **5.11** Memory integration: after sync, extract facts from important emails (client asks, deadlines, commitments) → write to memory. Entities auto-created for new senders.
- [ ] **5.12** Admin routes: `GET /integrations/google/status`, `POST /integrations/google/sync` (manual trigger), `POST /integrations/google/disconnect`.
- [ ] **5.13** Tests: OAuth flow with mocked Google, sync with mocked Gmail API, EmailAgent e2e with stubbed tools.

### Acceptance Criteria

1. Connect Google account → callback succeeds → integration row exists with encrypted tokens.
2. Manual sync pulls last 7 days of email into DB.
3. `/chat` "summarize my unread from clients this week" → EmailAgent runs, returns coherent summary citing real subjects.
4. `/chat` "draft a reply to the last email from John saying we're on track" → returns a draft; does not send.
5. Token refresh happens transparently when expired.
6. `make check` clean.

### Phase Gate Check

```bash
make check && python scripts/gmail_smoke.py
```

### Completion Log

---

## 9. PHASE 6 — Calendar Integration

**Goal.** Atlas can list events, find free time, create/reschedule events via `CalendarAgent`.

### Tasks

- [ ] **6.1** Reuse Google OAuth from phase 5; extend scopes to include `calendar.events` and `calendar.readonly` (re-auth flow if needed).
- [ ] **6.2** Models: `CalendarEvent(id, google_event_id, calendar_id, summary, description, start_at, end_at, attendees_json, location, status, created_at, updated_at)`.
- [ ] **6.3** `integrations/google/calendar_sync.py::sync(window_days=14)` — rolling 2-week window, upsert events.
- [ ] **6.4** Calendar tools:
  - `list_events(start, end)`
  - `find_free_time(duration_min, start?, end?, working_hours=9-18)` — respects Hamza's Asia/Karachi timezone
  - `check_conflicts(start, end)`
  - `create_event(summary, start, end, attendees?, description?)` — gated on confirmation
  - `reschedule_event(event_id, new_start, new_end)` — gated
- [ ] **6.5** `CalendarAgent` — registered; planner updated.
- [ ] **6.6** Memory integration: events become episodes; recurring meetings → entities ("Common Ground standup"); attendees auto-linked as person entities.
- [ ] **6.7** Tests with mocked Google Calendar API.

### Acceptance Criteria

1. Sync pulls upcoming events; `/chat` "what's on my calendar tomorrow" returns them.
2. "find me 2 hours free this week for deep work" returns valid slots in working hours.
3. "schedule a 30-min call with John next tuesday at 3pm" → CalendarAgent drafts the event, asks confirmation, creates on confirm.
4. `make check` clean.

### Phase Gate Check

```bash
make check && python scripts/calendar_smoke.py
```

### Completion Log

---

## 10. PHASE 7 — GitHub Integration

**Goal.** Atlas can query commits, PRs, issues, and summarize repo activity via `CodeAgent`.

### Tasks

- [ ] **7.1** GitHub PAT config — read from settings. Document required scopes in `docs/github_setup.md` (`repo`, `read:org` if needed).
- [ ] **7.2** `RepoWatch` model: `(id, user_id, full_name, is_active, last_synced_at)`. Seed with Hamza's repos (configurable list).
- [ ] **7.3** Models: `Commit(id, repo_id, sha, message, author_login, authored_at, files_changed_json, embedding)`, `PullRequest(id, repo_id, number, title, body, state, author, head_sha, base_branch, created_at, updated_at, merged_at?)`, `Issue(id, repo_id, number, title, body, state, labels, author, created_at, updated_at, closed_at?)`.
- [ ] **7.4** `integrations/github/sync.py` — paginated fetch since `last_synced_at`, upsert. Embed commit messages + PR titles/bodies.
- [ ] **7.5** Code tools:
  - `search_commits(query, repo?, author?, since?, limit=10)` — hybrid search
  - `get_pr_status(repo, number)`
  - `list_open_prs(repo?, author?)`
  - `summarize_repo_activity(repo, since)`
  - `find_commit_by_description(query)` — THE "where did we fix the UUID-to-slug bug" tool; vector search over commit messages
- [ ] **7.6** `CodeAgent` — registered; planner updated.
- [ ] **7.7** Memory integration: repos → entities; recurring collaborators → person entities with `collaborates_on` relations; significant PRs → episodes with references.
- [ ] **7.8** Tests with recorded GitHub API responses (vcr.py or custom fixtures).

### Acceptance Criteria

1. Configure 2 repos, sync pulls recent commits/PRs/issues.
2. `/chat` "what did Karsan push to cg-api yesterday"  → CodeAgent returns commit list with summaries.
3. `/chat` "find the commit where we fixed the empty-dict short-circuit bug" → returns the right commit via vector search.
4. `make check` clean.

### Phase Gate Check

```bash
make check && python scripts/github_smoke.py
```

### Completion Log

---

## 11. PHASE 8 — Proactive Layer

**Goal.** Atlas runs scheduled jobs and reacts to events — morning briefings, inbox alerts, PR nudges — and notifies via a pluggable notification bus.

**Infra decision for this phase.** This is where we reconsider Redis. APScheduler runs in-process with a Postgres jobstore (no Redis needed). The notification bus initially uses an in-process asyncio event bus — works for single-process dev. If we ever need WebSocket fan-out across multiple processes, we'll add Redis pubsub *or* use Postgres `LISTEN/NOTIFY` (which is already available and requires no new infra). The bus interface is designed so the backend is swappable.

### Tasks

- [ ] **8.1** APScheduler integration: `workers/scheduler.py` — AsyncIOScheduler, started on FastAPI lifespan startup, jobstore in Postgres (for persistence across restarts), misfire_grace_time configured.
- [ ] **8.2** Scheduled jobs registry `workers/jobs/__init__.py` — each job is a function registered at startup with its cron/interval.
- [ ] **8.3** Sync jobs: Gmail (every 5 min), Calendar (every 15 min), GitHub (every 10 min). Each uses a Postgres advisory lock (via `pg_try_advisory_lock`) to prevent overlap — no Redis needed.
- [ ] **8.4** Memory consolidation job (nightly at 2am Asia/Karachi) — runs the extractor over conversations from the past 24h.
- [ ] **8.5** Morning briefing job (8am Asia/Karachi, configurable):
  - Gathers: overnight high-importance emails, today's calendar, open PRs needing review, open tasks
  - Calls `BriefingAgent` (a new specialist) to compose
  - Writes as a `Briefing` record (model: `Briefing(id, generated_at, content_markdown, sections_json)`)
  - Publishes notification
- [ ] **8.6** `BriefingAgent` in `agents/specialists/briefing_agent.py`.
- [ ] **8.7** Event-driven triggers `workers/triggers.py`:
  - After Gmail sync: if new email from `client` tag with importance > threshold → publish `new_important_email` event
  - After Calendar sync: if new conflict detected → publish `calendar_conflict`
  - After GitHub sync: if review requested on Hamza's PR or new PR targeting his work → publish `github_nudge`
- [ ] **8.8** Notification bus `services/notifications/bus.py`:
  - `NotificationChannel` protocol with `async send(notification: Notification)`
  - `NotificationBackend` protocol for the pubsub layer — implementations: `InProcessBackend` (default, asyncio queue) and `PostgresListenNotifyBackend` (uses `LISTEN/NOTIFY`). Redis is explicitly future work.
  - Channel implementations: `WebSocketNotifier` (for Next.js app), `LogNotifier` (always on, dev)
  - `EmailNotifier` and desktop notifiers stubbed for later
  - `publish(notification)` fan-outs via the backend to all enabled channels
- [ ] **8.9** WebSocket endpoint `/ws/notifications` — client connects with JWT, server pushes notifications in real time. Uses the notification backend; for v1 with a single process, the in-process backend is fine.
- [ ] **8.10** User rules table `NotificationRule(id, user_id, event_type, conditions_json, channels, is_active)`. Default rules seeded on first run ("notify on new email from client", "notify on morning briefing").
- [ ] **8.11** Admin routes: `GET /briefings/latest`, `GET /briefings/{id}`, `POST /briefings/generate-now`, `GET /notifications/rules`, `POST /notifications/rules`.
- [ ] **8.12** Tests: scheduler boots and registers jobs, morning briefing generates given mocked data, WebSocket receives notification on publish, advisory lock prevents concurrent syncs.

### Acceptance Criteria

1. `make dev` → scheduler starts, logs show registered jobs with next-run times.
2. `POST /briefings/generate-now` → briefing generated, WebSocket clients receive push.
3. Simulate a new client-tagged email via a test fixture → trigger fires → notification published.
4. Restart API → jobs persist, next runs unchanged (thanks to Postgres jobstore).
5. Running two instances of the sync job back-to-back: second one skips cleanly due to advisory lock.
6. `make check` clean.

### Phase Gate Check

```bash
make check && python scripts/proactive_smoke.py
```

### Completion Log

---

## 12. PHASE 9 — Task/Delegation System

**Goal.** Long-running "do this for me" requests run in the background and report back.

### Tasks

- [ ] **9.1** `Task` model: `(id, conversation_id?, title, description, status, created_at, started_at?, completed_at?, result_json?, error?)`. Statuses: `pending | running | completed | failed | canceled`.
- [ ] **9.2** Task executor `services/tasks/executor.py` — async worker pool (asyncio task group), picks up `pending` tasks, dispatches to orchestrator with `task_mode=true` flag.
- [ ] **9.3** `TaskRequest` is a new planner outcome — if planner decides a request is long-running (> ~30s or multi-step with external calls), it creates a Task and returns "I'll work on this, I'll ping you when done."
- [ ] **9.4** Task tools: `create_task(title, description)`, `get_task(id)`, `list_tasks(status?, limit)`, `cancel_task(id)`.
- [ ] **9.5** On task completion, publish `task_completed` notification → notification bus.
- [ ] **9.6** Admin routes: `GET /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/cancel`.
- [ ] **9.7** History query: "what did you do yesterday?" → ListTasks + summarization.
- [ ] **9.8** Tests.

### Acceptance Criteria

1. `/chat` "draft reply suggestions for all unread client emails from this week" → planner creates a Task, immediate reply says so, task runs to completion, notification pushed.
2. `/chat` "what have you done today?" → lists completed tasks.
3. Cancel a running task → it stops cleanly, status `canceled`.
4. `make check` clean.

### Completion Log

---

## 13. PHASE 10 — Voice Input

**Goal.** Backend accepts audio, returns transcription.

### Tasks

- [ ] **10.1** `STTProvider` protocol in `services/stt/base.py` — `async transcribe(audio_bytes, mime_type) -> Transcription`.
- [ ] **10.2** `DeepgramProvider` implementation using the Deepgram SDK.
- [ ] **10.3** `POST /transcribe` — multipart upload (or raw audio body), returns `{text, confidence, duration_ms}`.
- [ ] **10.4** Rate limit per user. Tests with pre-recorded audio fixture.

### Acceptance Criteria

1. Upload a WAV → transcript returns correctly.
2. Swapping provider (e.g., to Whisper later) is a single file change.

### Completion Log

---

## 14. PHASE 11 — Observability + Eval Harness

**Goal.** Atlas is debuggable in production and has regression tests for agent behavior.

### Tasks

- [ ] **11.1** LangSmith integration — set `LANGCHAIN_TRACING_V2=true`, project name per environment. Verify traces appear for every orchestrator invocation.
- [ ] **11.2** Instrument custom spans for non-LLM work (DB queries > 100ms, external API calls) via a small decorator.
- [ ] **11.3** Structured logs wired to include `trace_id` for cross-referencing with LangSmith.
- [ ] **11.4** Eval harness `evals/` — a set of YAML-defined test cases:
  ```yaml
  - name: recall_stack_preference
    seed: seeds/hamza_basics.json
    turns:
      - user: "I prefer pnpm over npm"
      - user: "what's my package manager preference?"
    assertions:
      - response_contains: ["pnpm"]
      - fact_written: { subject: hamza, predicate: prefers, object: pnpm }
  ```
- [ ] **11.5** Eval runner `evals/run.py` — executes cases against a fresh DB state, reports pass/fail.
- [ ] **11.6** `make eval` target. Add to CI later.
- [ ] **11.7** Admin dashboard endpoints: `/admin/stats` (msg counts, fact counts, task stats), `/admin/recent-traces` (pulls recent LangSmith trace URLs).

### Acceptance Criteria

1. Every `/chat` request produces a trace in LangSmith with all nodes visible.
2. `make eval` runs the full suite, all pass.
3. A regression (e.g., remove memory injection) causes specific evals to fail.

### Completion Log

---

## 15. PHASE 12 — Hardening + Deployment

**Goal.** Atlas runs on Hamza's EC2, reachable over HTTPS, with proper secrets, monitoring, and backups.

**Deployment approach.** Start with the simplest thing that works: systemd + Python venv + native Postgres on the EC2 instance. No Docker required. We can containerize later if we decide to run multiple instances or migrate to managed infra.

### Tasks

- [ ] **12.1** Provision EC2 (Ubuntu 22.04 LTS recommended). Install: Python 3.11, Postgres 16, pgvector (apt-installable on Linux — much easier than Windows), nginx, certbot.
- [ ] **12.2** systemd service files: `atlas-api.service` (uvicorn workers). Scheduler runs in-process with the API for v1; split out later if needed.
- [ ] **12.3** Nginx config: TLS termination, `/api/` → FastAPI, `/ws/` → WebSocket upgrade. HTTP/2 on.
- [ ] **12.4** Let's Encrypt via certbot for the subdomain.
- [ ] **12.5** Secrets via environment file loaded by systemd (`/etc/atlas/atlas.env`, root-owned 600). Not in repo.
- [ ] **12.6** DB backups — daily `pg_dump` cron to S3, 7-day retention.
- [ ] **12.7** Health monitoring — simple: cron that curls `/health` and emails on failure. Upgrade to UptimeRobot/BetterStack later.
- [ ] **12.8** Log shipping — for now, rely on `journalctl` + file logs; mention future upgrade path to Grafana Loki.
- [ ] **12.9** Deploy script `scripts/deploy.sh` — ssh to EC2, git pull, `poetry install --no-dev`, migrate, restart systemd units, smoke-check `/health`.
- [ ] **12.10** Document runbook in `docs/runbook.md`: common ops (restart, rollback, backup restore, view logs, rotate OAuth tokens).
- [ ] **12.11** Rate limiting on public endpoints (slowapi middleware).
- [ ] **12.12** Security pass: no secrets in logs, all user input validated via Pydantic, CORS locked to known origins.
- [ ] **12.13** Decide: does the proactive layer need Redis yet? If running one API process, no. If scaling out, add Redis pubsub behind the existing `NotificationBackend` interface. Document the decision.

### Acceptance Criteria

1. `https://atlas.yourdomain.com/health` returns 200 over TLS.
2. Daily backup visible in S3.
3. Restarting the EC2 instance → Atlas comes back up clean via systemd, jobs resume.
4. Runbook is complete enough that a new engineer could handle a restart.

### Completion Log

---

## 16. Decisions & Deviations

Log every decision that deviates from this plan, with reasoning.

Format: `YYYY-MM-DD — [phase N] — Decision — Reason`.

- 2026-04-19 — [plan] — Gemini chosen as default LLM over Claude/GPT — free tier, provider interface makes swap trivial later.
- 2026-04-19 — [plan] — Postgres + pgvector over Pinecone — self-hosted, portfolio-friendly, one less external service.
- 2026-04-19 — [plan] — APScheduler over Celery — async-native, simpler for single-node deploy, good enough for this scale.
- 2026-04-19 — [plan] — Deferred frontend to a separate track — backend must be stable first.
- 2026-04-19 — [plan] — Dropped Docker from dev workflow — native Windows Postgres + Poetry is simpler, faster, zero orchestration overhead for a solo single-machine build.
- 2026-04-19 — [plan] — Dropped Redis from phases 1–7 — no distributed state or pubsub needed at this scale. In phase 8, using Postgres advisory locks for job coordination and an in-process notification bus. Redis becomes an optional phase-12 addition if we need multi-process fan-out.
- 2026-04-19 — [plan] — Deployment via systemd (not Docker) — matches the "keep it simple" stance; containerization is a future optimization, not a requirement.
- 2026-04-19 — [phase 1] — Switched dev database from native Windows Postgres to Neon — Avoid Windows pgvector compile/install friction; Neon ships managed Postgres 17 with pgvector enabled. `DATABASE_URL` uses `postgresql+asyncpg://…?sslmode=require` against Neon’s pooler endpoint; SQLAlchemy async + Alembic unchanged. Single `atlas` database; extension created with `psql`/`CREATE EXTENSION vector` on Neon.

---

## 17. Open Questions / Future Phases

Park ideas here; don't build them without promoting to a phase first.

- Multi-user / real auth (if open-sourced as a template)
- WhatsApp integration (phase 13?)
- Slack integration
- Linear / Jira integration
- Voice output via ElevenLabs (currently browser-native Web Speech)
- Desktop notifications via a companion Tauri app
- Mobile? (explicitly out of scope — revisit never)
- Fine-tuned small model for classification tasks (cost reduction)
- MCP server exposing Atlas to Claude Desktop / Cursor
- Dockerization (if we ever need multi-instance deploys or team onboarding)
- Redis (if pubsub fan-out across processes becomes necessary)

---

*End of plan. Update the completion logs and checkboxes as you go.*