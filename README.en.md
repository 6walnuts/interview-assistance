# AI Interview Coach

[中文](README.md) | **English** | [Español](README.es.md)

An **AI interview coaching platform** for SDE / Backend / Infra / AI-Infra candidates. Not a one-shot mock-interview tool, but a complete loop:

```
Learn → targeted practice → mock interview → automatic scoring → review → personalized study plan → practice again
```

Candidate product names: **Offerloop · Hirely · MockMentor · Interview Forge · SignalPrep** (see `docs/01-product-architecture.md`).

## Documentation

| Doc | Contents |
|---|---|
| `docs/01-product-architecture.md` | Product positioning, user flows, MVP scope, page structure, priorities |
| `docs/02-tech-architecture.md` | Frontend / backend / agents / sandbox / deployment architecture |
| `docs/03-data-model.md` | Data model for all 16 tables (DDL in `database/init.sql`) |
| `docs/04-api-design.md` | REST API design (schemas / errors / permissions) |
| `docs/05-agent-prompts.md` | System prompts for the 4 core agents |
| `docs/06-development-plan.md` | Project layout + Phase 1-4 development plan |

## Repository layout

```
apps/web        Next.js 14 frontend (TypeScript + Tailwind + Monaco)
services/api    FastAPI backend (SQLAlchemy + 7 agents + Docker sandbox)
database/       Postgres DDL + Alembic migration scaffold
infra/          docker-compose + sandbox images
packages/       Reserved: shared TS types package
docs/           Design docs
```

## Running locally

### 0. Environment variables

```bash
cp .env.example services/api/.env
# Runs without any API key: with MOCK_AI=true every agent returns a
# deterministic mock, so the whole interview → scoring → study-task loop
# works offline.
```

**Multiple AI providers** are supported via `LLM_PROVIDER`:

| Provider | Config | Default model |
|---|---|---|
| OpenAI | `LLM_PROVIDER=openai LLM_API_KEY=sk-...` | gpt-4o-mini |
| DeepSeek | `LLM_PROVIDER=deepseek LLM_API_KEY=sk-...` | deepseek-chat |
| Kimi (Moonshot) | `LLM_PROVIDER=kimi LLM_API_KEY=sk-...` | kimi-latest (overseas accounts add `LLM_BASE_URL=https://api.moonshot.ai/v1`) |
| Claude (Anthropic) | `LLM_PROVIDER=anthropic LLM_API_KEY=sk-ant-...` | claude-opus-4-8 (cheaper: `LLM_MODEL=claude-haiku-4-5`) |

DeepSeek/Kimi use the OpenAI-compatible interface; Claude uses the official `anthropic` SDK.
Any OpenAI-compatible self-hosted gateway works via `LLM_BASE_URL`. Remember to set `MOCK_AI=false`.

### 1. Backend (SQLite by default, zero-dependency start)

> ⚠️ **Requires Python ≥ 3.10 (3.12 recommended). Check your version first:**
>
> ```bash
> python3 --version
> ```
>
> **macOS note**: the system `python3` shipped with the Xcode command-line
> tools is **3.9** (at `/usr/bin/python3`) and fails on this project with
> `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`.
> If your version is below 3.10, install a newer one and **pin the version
> explicitly when creating the venv**:
>
> ```bash
> brew install python@3.12
> ```

```bash
cd services/api
python3.12 -m venv .venv          # pin the version — don't use bare python3
source .venv/bin/activate
# Windows: py -3.12 -m venv .venv then .venv\Scripts\activate
.venv/bin/python --version        # checkpoint: must print 3.12.x before you continue!
pip install -r requirements.txt
python -m app.seed                # create tables + seed topics/questions/quizzes
uvicorn app.main:app --reload --port 8000
```

**Pitfall tip**: `source` activation only applies to the current terminal
window. When in doubt, use the venv's full paths — they can never pick the
wrong interpreter:

```bash
.venv/bin/python -m app.seed
LOCAL_MODE=true SANDBOX_MODE=subprocess .venv/bin/uvicorn app.main:app --reload --port 8000
```

#### Common errors

| Error | Cause | Fix |
|---|---|---|
| `TypeError: unsupported operand type(s) for \|: 'type' and 'NoneType'` | Command ran on Python ≤3.9 (venv not activated, or venv built with 3.9) | See next row |
| Same, but `.venv/bin/python -m app.seed` also fails | venv was created with 3.9 (or mixed versions) | `rm -rf .venv`, recreate with `python3.12 -m venv .venv`, reinstall deps |
| `psycopg2.OperationalError: connection ... port 5432 failed` | `DATABASE_URL` in `.env` points at a Postgres that isn't running | Change to `DATABASE_URL=sqlite:///./dev.db` (or delete the line for the default) |
| `command not found: python3.12` | Homebrew installed it but it's not on PATH | Use the full path `/opt/homebrew/bin/python3.12` (Intel Mac: `/usr/local/bin/python3.12`) |
| Frontend shows `502` + quota/balance message | LLM provider account has no credit or the key is invalid | Top up as prompted, or switch `LLM_PROVIDER` |
| `ChunkLoadError` (`/_next/undefined`) or "xxx is not a function" right after pulling updates | Stale/mixed Next.js build cache | Stop the frontend → `rm -rf .next node_modules/.cache` → restart → hard-refresh the browser (Cmd+Shift+R) |

**Single-user passwordless mode**: for personal local use you can skip
registration/login; everything is saved under one local account:

```bash
LOCAL_MODE=true SANDBOX_MODE=subprocess uvicorn app.main:app --reload --port 8000
```

The frontend then skips the login page and lands on the Dashboard (the nav
shows "Local mode"). Data still persists in `services/api/dev.db` (SQLite);
delete that file to reset. Note: under LOCAL_MODE anyone who can reach the
port is the same account — local machine only.

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd apps/web
npm install
npm run dev                 # http://localhost:3000
```

### 3. Code sandbox (optional, safe execution for coding interviews)

Supports **Python / JavaScript / Go / Java / C++**:

```bash
infra/sandbox/build.sh    # build all 5 language images
# set SANDBOX_MODE=docker (default) in services/api/.env
# without Docker, dev can use SANDBOX_MODE=subprocess (no isolation, dev only;
# requires the local toolchains python3/node/go/javac/g++)
```

- Python and JavaScript: the question's test cases are auto-graded
- Go / Java / C++: compiled and run as a whole program (CoderPad style); the
  candidate self-tests in main, compile errors and output are returned as-is;
  the interviewer and Scoring Agent evaluate from code + output

Sandbox limits: no network (`--network none`), CPU/memory caps (relaxed to
512-768m for compiled languages), `--pids-limit` (fork-bomb protection),
read-only root FS + executable tmpfs (build artifacts), nobody user, no host
env vars passed in, host-side timeout kill (compiled languages get an extra
20-30s compile allowance).

### 4. Full Docker stack (Postgres + Redis + API)

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

### 5. Tests

```bash
cd services/api && .venv/bin/python -m pytest tests -q
```

Coverage: auth, ownership isolation, the full interview loop (create →
messages → hints → run code → end → report → auto-generated ≥3 study tasks →
idempotency), task completion updating Mastery, progress endpoints.

## Classic system-design question bank

`app/seed_questions.py` ships originally-written classic system-design
questions covering the industry's high-frequency themes: infrastructure
classics (URL shortener, KV store, message queue, payments, exchange, …) plus
ML/GenAI system design (visual search, recommenders, RAG, text-to-image, …).
Every question carries quantified constraints and a scoring rubric — the
rubric is the Scoring Agent's checklist of expected discussion points. New
system_design interviews draw from the bank by difficulty + focus areas;
re-running `python -m app.seed` merges new questions into an existing
database idempotently.

## Study plan & chapter quizzes

- **Study plan**: after onboarding, the Learning Planner Agent generates a
  week-by-week task sequence from your interview date and weekly hours
  (`POST /api/plan/generate`; the Tasks page groups by week; regenerate any
  time — completed tasks are kept as history).
- **Chapter quizzes**: every topic has its own question pool
  (`GET /api/quiz/{topic_slug}`); when it runs low the Quiz Generator Agent
  tops it up. Submissions (`POST /api/quiz/{topic_slug}/submit`) update
  Mastery, record mistakes into common_mistakes, and a score ≥60%
  auto-completes the matching study task.

## Voice input & read-aloud

Both the interview room and the Learn page coach support voice (OpenAI audio
APIs, requires `LLM_PROVIDER=openai`):

- **🎙 Voice input**: click the mic to record, click again to stop; the
  recording is transcribed into the input box (`POST /api/voice/transcribe`,
  model `gpt-4o-mini-transcribe`, ~$0.003/min).
- **🔊 Auto-read**: when enabled, interviewer/coach replies are read aloud
  (`POST /api/voice/tts`, model `gpt-4o-mini-tts`, ~$0.015/min; voice set
  via `VOICE_TTS_VOICE`).
- With `MOCK_AI=true` both endpoints return a fixed transcript and a short
  silent WAV, so offline/testing still works.
- The browser asks for microphone permission; Chrome/Edge/Safari all work on
  `localhost`.

**📞 Live voice calls** (interview room header): talk to the interviewer like
a phone call. The browser connects directly to the OpenAI Realtime API
(`gpt-realtime`) over WebRTC; the backend only mints a 10-minute ephemeral
secret (`POST /api/voice/realtime-session`) so your API key never reaches the
frontend. Both sides are transcribed live into the chat panel and persisted
to `interview_messages` (`POST /api/voice/realtime-transcript`), so scoring,
reports, and study plans work as usual. Requires a real OpenAI key
(`MOCK_AI=false`); roughly $0.3-0.5 per session.

The voice interviewer drives the full 12-stage state machine via function
calling: `advance_stage` (the stage bar follows live) and
`record_observation` (private evaluation notes). Tool calls are relayed
through `POST /api/voice/realtime-tool`; stage changes and observations are
stored as system messages, and `internal_observation` still goes only to the
Scoring Agent — never into any API response. The scoring red line stands: the
voice interviewer interviews, it does not grade.

## The core loop (one chain)

```
POST /api/interviews          Interview Planner picks the question, Mock Interviewer opens
POST .../messages             Interviewer state machine advances (internal_observation stored, never shown)
POST .../run-code             Docker sandbox execution + test-case grading
POST .../end                  Scoring Agent grades independently → interview_reports
                              Review Task Generator → review_tasks + learning_tasks(≥3)
GET  .../report               Report page; GET /api/tasks shows the study plan
```

## Production migrations

```bash
cd database/alembic
DATABASE_URL=postgresql://... alembic revision --autogenerate -m "init"
DATABASE_URL=postgresql://... alembic upgrade head
```

## Security notes

- All secrets come from environment variables; zero hardcoding in the repo
  (`.env.example` is the template).
- JWT HS256 + PBKDF2 password hashing; every resource endpoint checks
  ownership (403).
- `interview_messages.internal_observation` never appears in any API response.
- All LLM output is strictly validated against Pydantic schemas; one automatic
  retry on failure, then a clean error.
