# ORCAI — AI-first recruiting platform for Indian staffing agencies

Single-vendor talent matchmaking for US staffing: aggregates W2 bench, client contracts
and free sourcing channels (WhatsApp / Telegram), then scores seekers against
requisitions with an AI engine gated by a **human-in-the-loop (HITL)** confidence
checkpoint — compliant with DPDPA-2023 consent obligations out of the box.

## Stack

| Layer       | Tech                                                  |
| ----------- | ----------------------------------------------------- |
| Frontend    | Next.js 15 (App Router) + React 19 + TypeScript + Tailwind |
| API         | FastAPI (Python 3.12+)                                 |
| DB          | PostgreSQL 16 (dev default: SQLite via `DATABASE_URL`) |
| AI          | OpenAI-compatible LLM (optional) with deterministic offline fallback |

Everything runs with **zero external dependencies** — when `OPENAI_API_KEY` is absent
every parser and the matcher use rule-based engines, so the whole product works
offline. LLM keys only upgrade output quality, they are never required.

## Quick start (local)

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate    |    macOS/Linux: source .venv/bin/activate
pip install -e .
pip install pytest pytest-asyncio ruff          # dev tools (installed manually)
cp ../.env.example .env                          # optional
python -m app.seed                               # demo data
python -m uvicorn app.main:app --port 8000
```

Demo login: `owner@taproot.io` / `Orcai@12345` (agency `taproot-consulting`).

### 2. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open http://localhost:3000 — log in with the demo credentials above.

## Environment (`.env.example`)

- `DATABASE_URL` — `sqlite:///./orcai.db` (dev) or `postgresql+psycopg://...`
- `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL` — optional AI upgrade path
- `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `TELEGRAM_BOT_TOKEN` — inbound channels
- `NEXT_PUBLIC_API_URL` — backend base (frontend)

## What works (v1)

- **Auth + multi-tenancy** — agency signup, JWT login, role-based access (owner / recruiter / client)
- **Contract / requisition parsing** — paste raw client requests; skills, role, visa needs,
  rate, remote flag, contract dates and client info extracted automatically
- **Resume parsing + dedupe** — `.pdf` / `.docx` / `.txt` upload; name/email/phone/skills/experience
  extracted; duplicates resolved via canonical key (email → phone → name) and merged, never doubled
- **Matching engine + HITL gate** — weighted scoring (skills/experience/visa/location/title);
  Tier A (≥85) auto-approves, high-confidence rejects skipped, the rest queued for a recruiter
- **WhatsApp / Telegram inbound** — webhook + simulator turns incoming chats into verified seekers
- **DPDPA consent ledger** — opt-in logging, withdrawal and right-to-erasure per seeker

## API (base `/api/v1`)

`/auth/*`, `/contracts` (+`/clients`), `/seekers` (+`/dedupe-check`, `/upload`),
`/matches` (+`/run`), `/hitl` (+`/matches/{id}/review`), `/inbound` (+`/webhook`,
`/message`), `/consent` (+`/{id}/withdraw`, `/{id}/erase`), `/billing` (+`/plans`,
`/subscription`, `/dashboard`), `/health`.

## Tests & lint

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest        # 9 tests
.\.venv\Scripts\python.exe -m ruff check app tests
cd ../frontend
npm run build                                # type-checks + builds all pages
```

## Production (Docker)

```bash
cp .env.example .env   # set DATABASE_URL to postgres in compose
docker compose up --build
```

`postgres:16` + backend :8000 + frontend :3000.

## Repo map

```
backend/app/core        config, DB session, security (JWT/bcrypt)
backend/app/models      SQLAlchemy models (agency, user, client, contract, seeker, match, inbound, consent, subscription)
backend/app/schemas     Pydantic request/response models
backend/app/api/v1      REST routers
backend/app/services    LLM wrapper, parsers, dedupe, matcher, inbound ingest, seeker upsert
backend/app/seed.py     idempotent demo data
frontend/app            Next.js app (auth BFF + (app) pages)
frontend/middleware.ts  BFF proxy: /api/* -> FastAPI with httpOnly-token injection
frontend/lib            typed API client + shared types
```