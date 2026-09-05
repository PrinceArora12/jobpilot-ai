# JobPilot AI

Real-time AI-powered job discovery, matching, rapid-application, and
application-tracking platform.

> **Product promise:** When a relevant opportunity appears, JobPilot AI
> detects it quickly, evaluates it instantly, and gets your application
> ready — or submits it through a permitted automated workflow — before the
> opportunity gets crowded.

All 12 phases of the build are complete. This README documents the full
system as delivered: architecture, every feature, how to run it, and how
each phase was verified.

## Build status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation — repo, Docker, Postgres, Redis, FastAPI, React, auth, DB models, basic dashboard | ✅ Done |
| 2 | Profile (education, skills, experience, projects, certifications) | ✅ Done |
| 3 | Resume intelligence (PDF/DOCX parsing, structured extraction) | ✅ Done |
| 4 | Job engine (schema, source adapters, normalization, dedup, search) | ✅ Done |
| 5 | AI matching (job/profile analyzers, match score, missing skills) | ✅ Done |
| 6 | Application tracking (DB, statuses, history, notes) | ✅ Done |
| 7 | Rapid Apply (watcher, Redis priority queue, fast eligibility, latency tracking) | ✅ Done |
| 8 | Browser automation (Playwright, form detection/field mapping, mock testing) | ✅ Done |
| 9 | AI application assistant (question answering, resume tailoring) | ✅ Done |
| 10 | Automation (rules, limits, blocklists, notifications, pause/resume/stop) | ✅ Done |
| 11 | Analytics (funnel, conversion rates, resume performance, timeline) | ✅ Done |
| 12 | Production hardening (rate limiting, audit log, security headers, full verification) | ✅ Done |

## Problem statement

Good jobs — especially internships and fresher roles — get crowded within
minutes of being posted. JobPilot AI's job is to close that gap: watch
permitted sources continuously, understand whether a new posting fits a
candidate's real profile, and get a compliant application in front of the
employer as fast as the workflow allows — while refusing to touch anything
that requires bypassing security, fabricating qualifications, or violating a
portal's rules. See [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) for the full
list of hard constraints this project observes at every phase.

## Architecture

```
  Job Sources → Watcher → Normalize → Dedup → Automation Rules Gate
       (blocklists / rate limits, spec §60-62 — checked before matching)
                              ↓
                     Fast Eligibility Filter
                              ↓
                    AI Match Engine (scored)
                              ↓
                Redis Priority Queue (P0–P3)
                              ↓
        Rapid Apply Worker  →  Playwright Automation
     (mock-form only; refuses          ↓
      any real portal outright)  Application record
                              ↓
              PostgreSQL (source of truth)
                              ↓
      Notifications · Audit Log · Analytics (funnel/conversion/resume perf)
```

Everything above the Redis queue runs synchronously (and is exercised
directly by `POST /api/rapid-apply/run-cycle`); in production, Celery beat
triggers the same code every minute via the `worker`/`beat` services in
`docker-compose.yml`.

## Full project layout

```
jobpilot-ai/
│
├── frontend/                         React + TypeScript + Vite + Tailwind
│   ├── src/
│   │   ├── pages/                    Dashboard, Jobs, JobDetail, RapidApply,
│   │   │                             Applications, ApplicationDetail, Resume,
│   │   │                             Profile, Analytics, Automation, Settings,
│   │   │                             Login, Register, ComingSoon (Interviews)
│   │   ├── layouts/                  AuthLayout, AppLayout (sidebar + notification bell)
│   │   ├── components/               ProtectedRoute, EntityListEditor, JobCard
│   │   ├── hooks/                    useAuth (JWT session context)
│   │   ├── services/                 one file per API area (axios wrappers)
│   │   ├── types/                    one file per API area (TS interfaces)
│   │   └── App.tsx                   route table
│   └── Dockerfile                    dev / build / nginx production stages
│
├── backend/                          FastAPI + SQLAlchemy (async) + PostgreSQL
│   ├── app/
│   │   ├── api/                      auth, profile, resumes, jobs, mock_jobs,
│   │   │                             matches, applications, rapid_apply,
│   │   │                             mock_forms, assistant, automation,
│   │   │                             notifications, analytics, audit, health
│   │   ├── models/                   user, profile, resume, job, job_match,
│   │   │                             application, rapid_apply, automation
│   │   │                             (rules + notifications), audit_log
│   │   ├── services/                 job_ingestion, job_normalizer, job_dedup,
│   │   │                             match_service, eligibility, resume_parser,
│   │   │                             resume_tailor_service, rapid_apply_service,
│   │   │                             priority_queue, automation_rules_service,
│   │   │                             notification_service, analytics_service,
│   │   │                             audit_service, profile_service, storage
│   │   ├── agents/                   application_assistant (Q&A, confidence-gated)
│   │   ├── automation/               browser_automation (Playwright), field_mapper
│   │   ├── ai/                       provider-agnostic AI abstraction (mock/openai/anthropic)
│   │   ├── worker/                   celery_app, tasks (Rapid Apply cycle scheduling)
│   │   ├── core/                     config, security (JWT/bcrypt), rate_limit
│   │   │                             (Redis fixed-window), security_headers, logging
│   │   └── main.py
│   ├── tests/                        22 files, 139 passing tests (in-memory SQLite)
│   ├── alembic/                      migrations 0001–0010
│   ├── requirements.txt
│   └── Dockerfile                    installs Playwright + Chromium for automation
│
├── docker-compose.yml                postgres, redis, backend, frontend, worker, beat
├── .env.example
├── docs/
│   └── COMPLIANCE.md
└── README.md
```

## Feature tour

**Profile & resume (Phases 2–3).** Education, experience, projects,
certifications, and skills, plus multi-resume upload (PDF/DOCX) with
automatic text extraction and structured parsing into the same fields.

**Job engine & matching (Phases 4–5).** A pluggable source-adapter layer
(a full mock source is included for end-to-end testing without hitting any
real job board), normalization, content-hash deduplication, and an AI
match engine that scores skills/education/experience/location/role fit,
lists missing skills, and explains the score — the AI layer only ever
reformats grounded facts, never invents qualifications.

**Application tracking (Phase 6).** Every application has a full status
history (`ApplicationEvent` audit trail), notes, and a resume attached.

**Rapid Apply (Phase 7).** A watcher drains new postings, screens every
opted-in user, and queues qualifying matches into a Redis priority queue
(P0–P3 by score). Every pipeline stage is timestamped
(`first_seen_at` → `detected_at` → `normalized_at` → `matched_at` →
`queued_at` → `application_started_at` → `application_completed_at`) so
latency is measured, never assumed.

**Browser automation (Phase 8).** Real Playwright automation fills and
submits application forms — but **only** against this app's own mock
application-form server. Any non-mock source is refused outright. CAPTCHA,
MFA, and unmapped required fields are hard stops ("needs_manual_review"),
never guessed past.

**AI application assistant (Phase 9).** Answers application questions only
when the answer is grounded in the user's actual profile/resume/job match
(skills, years of experience, education, location); anything ungrounded
(salary, visa status, notice period, motivation essays) returns
`NEEDS_USER_INPUT` instead of fabricating an answer. Resume tailoring
suggests a reordering of existing skills for a specific job and validates
that the approved order is an exact permutation of the original set before
applying it — nothing can be added or removed.

**Automation controls (Phase 10).** Per-user `AutomationRule`: a global
running/paused/**stopped** kill switch, hourly/daily/per-company
application caps, and blocklists (source, company, keyword) — all enforced
*before* matching runs, regardless of how good a match looks. An in-app
notification feed records every submission, manual-review fallback, and
rate-limit pause, surfaced both as a bell dropdown in the app header and
as a full feed on the Automation page.

**Analytics (Phase 11).** A funnel built from each application's full
status *history* (not just its current status), so an application that
reached "interview" before being rejected still counts as having reached
that stage. Submitted/response/interview/offer conversion rates, a 30-day
discovered-vs-submitted timeline, and per-resume performance (which
resume version gets the most responses).

**Production hardening (Phase 12).** Redis-backed fixed-window rate
limiting on `/auth/register`, `/auth/login`, and
`/rapid-apply/run-cycle`; an account-wide, append-only audit log (auth
events, application status changes, automation rule/state changes, resume
deletions) surfaced on the Settings page; baseline security response
headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, HSTS when `APP_ENV=production`); a startup guard that
refuses to boot with `APP_ENV=production` while `SECRET_KEY`/`JWT_SECRET`
still hold their development placeholder values; and real `worker`/`beat`
Celery services in `docker-compose.yml` (previously a placeholder comment)
running the exact same `rapid_apply_service.run_cycle` code the manual
API endpoint calls.

## Tech stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, React Router,
  TanStack Query, Recharts, Lucide Icons
- **Backend**: Python, FastAPI, SQLAlchemy 2.0 (async), Pydantic, Alembic,
  PostgreSQL
- **Background processing**: Redis (priority queue + rate limiting),
  Celery (worker + beat)
- **Browser automation**: Playwright — only ever targets this app's own
  mock application-form server
- **AI**: provider-agnostic abstraction layer (`AI_PROVIDER` env var —
  `openai` / `anthropic` / `mock`)
- **Auth**: JWT, bcrypt password hashing
- **Deployment**: Docker, Docker Compose

## Installation & setup

### Prerequisites

- Docker + Docker Compose **or** Python 3.11+, Node 20+, PostgreSQL 16,
  Redis 7 installed natively
- `cp .env.example .env` at the repo root (and `cp frontend/.env.example
  frontend/.env` if running the frontend outside Docker)

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

This starts six services: `postgres`, `redis`, `backend` (runs Alembic
migrations on start, then serves the API), `frontend` (Vite dev server),
`worker` (Celery, processes Rapid Apply cycles), and `beat` (schedules one
Rapid Apply cycle per minute — spec section 57's watcher cadence).

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173
- Postgres: localhost:5432 · Redis: localhost:6379

### Option B — Run natively

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium   # needed for Phase 8 automation
cp ../.env.example .env   # edit DATABASE_URL/REDIS_URL if not using defaults
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

**Celery worker + beat (optional, for automatic Rapid Apply cycles)**

```bash
cd backend && source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info   # terminal 1
celery -A app.worker.celery_app beat --loglevel=info     # terminal 2
```

Without these, Rapid Apply still works fully via the manual
`POST /api/rapid-apply/run-cycle` endpoint (which the Rapid Apply page's
"Run cycle now" button calls) — the worker/beat services just automate
that trigger every minute.

### Database setup (native, no Docker)

```bash
sudo -u postgres psql -c "CREATE ROLE jobpilot LOGIN PASSWORD 'jobpilot';"
sudo -u postgres psql -c "CREATE DATABASE jobpilot OWNER jobpilot;"
cd backend && alembic upgrade head
```

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -q
```

**139 tests** across 22 files run against an in-memory SQLite database via
dependency override (no Postgres/Redis required for most of them — Rapid
Apply and rate-limiting tests do use a real local Redis instance, matching
production, and are isolated from each other via autouse fixtures that
flush the relevant key namespaces before/after each test). Coverage
includes: auth, profile, resumes, job dedup/normalization, matching engine,
applications, Rapid Apply (queue, latency, automation rules enforcement),
browser automation (against a real local HTTP server), the application
assistant, automation rules/notifications, analytics (funnel/conversion/
resume performance/timeline), the audit log, and rate limiting/security
headers.

```bash
cd frontend
npm run build   # type-checks + builds
npm run lint    # eslint, 0 errors
```

## API reference

Interactive OpenAPI docs are served by FastAPI at `/docs` (Swagger UI) and
`/redoc` once the backend is running. Route groups:

```
/api/auth              register, login, me
/api/profile           education, experience, projects, certifications, skills
/api/resumes           upload, list, get, update, delete, set-primary
/api/jobs               list/search/get, sync from sources
/api/mock                mock job posting + mock application form (test-only sources)
/api/matches             compute/list match scores against a job
/api/applications         create/list/get/update, notes, auto-submit retry
/api/rapid-apply          settings, run-cycle, queue, stats
/api/assistant            answer application questions, tailor-resume preview/apply
/api/automation           rules (get/update), start, pause, stop
/api/notifications        list, unread-count, mark read, mark all read
/api/analytics            summary, funnel, resume-performance, timeline
/api/audit-log            list (account-wide, paginated)
/api/health               liveness check
```

## AI architecture

JobPilot AI deliberately avoids one giant agent. Specialized, narrowly
scoped services live under `app/agents/` and `app/ai/`: the AI provider
abstraction is only ever called to reformat facts a deterministic step has
already grounded — matched skills, resume content, profile fields — never
to invent a qualification or answer a question with no grounded source.
Every place this boundary matters is enforced with a hard code invariant,
not just a prompt instruction: resume tailoring validates the approved
skill order is an exact permutation of the original set; the application
assistant returns `NEEDS_USER_INPUT` rather than guessing; browser
automation stops outright on CAPTCHA/MFA/an unmapped required field.

## Rapid Apply architecture

Detection → normalization → deduplication → **automation rules gate**
(blocklists + rate limits, checked first and unconditionally) → fast
eligibility → AI match → Redis priority queue (P0 highest match / P1 / P2
/ P3) → queue processing → Playwright automation (mock-form only) or an
honest `needs_manual_review` fallback. Every stage timestamps itself so
real latency is measured and reported — never assumed or faked.

## Security

- Passwords hashed with bcrypt; JWTs signed with a server-side secret
  (`JWT_SECRET`), never exposed to the frontend
- `.env` is git-ignored; `.env.example` only ever contains placeholders
- CORS is restricted to configured origins
- Baseline security response headers on every request
  (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, a restrictive
  `Permissions-Policy`, and HSTS once `APP_ENV=production`)
- Redis-backed rate limiting on `/auth/register`, `/auth/login`, and
  `/rapid-apply/run-cycle`, keyed per client IP; fails open (never blocks
  real traffic) if Redis itself is unreachable
- An account-wide, append-only audit log records auth events, application
  status changes, automation rule/state changes, and resume deletions —
  visible to each user for their own account on the Settings page
- A startup check refuses to boot with `APP_ENV=production` while
  `SECRET_KEY`/`JWT_SECRET` still hold development placeholder values
- **JobPilot AI never asks for, stores, or automates using a user's
  credentials on any external job portal** (LinkedIn, Indeed, Workday,
  etc.) — automation only ever targets this app's own mock form server;
  see `docs/COMPLIANCE.md` for the full list of hard constraints

## Deployment

`docker-compose.yml` is the local development target and also documents
the full production topology: `postgres`, `redis`, `backend` (runs
migrations then serves the API), `frontend` (dev server; a separate
`production` Dockerfile stage builds and serves static assets via nginx),
`worker` (Celery, processes tasks), and `beat` (schedules Rapid Apply
cycles). For an actual production deployment, additionally: point
`DATABASE_URL`/`REDIS_URL` at managed instances, set real `SECRET_KEY`/
`JWT_SECRET` values and `APP_ENV=production` (the app refuses to start
otherwise with placeholder secrets), terminate TLS in front of the API,
and run the `frontend` image's `production` build stage instead of `dev`.

## Verification performed

Every phase was verified the same way before moving to the next: write
the code → run the backend test suite (in-memory SQLite) → apply the
Alembic migration against a real local PostgreSQL instance → live
`uvicorn`/Redis smoke tests with `curl` → `npm run build` + `npm run lint`
(must be clean) → a live Playwright browser script driving the real
running frontend against the real running backend end-to-end → clean up
background processes. As of this delivery:

- `pytest -q` → **139 passed**
- All 10 Alembic migrations applied cleanly against a real local
  PostgreSQL 16 instance
- `npm run build` → clean Vite production build, 0 TypeScript errors
- `npm run lint` → 0 errors
- Live Playwright end-to-end scripts passed for every phase from Rapid
  Apply through production hardening, driving the real dev server against
  the real backend/Postgres/Redis — including: the full Rapid Apply →
  automation → notification pipeline; automation rule/blocklist/rate-limit
  enforcement and the global Stop button; the Analytics page rendering a
  real funnel, conversion rates, and timeline computed from real data; and
  the Settings page's audit log reflecting real register/login/application/
  automation events
- `docker compose config` → the full 6-service compose file (including the
  now-real `worker`/`beat` Celery services) validates cleanly (the build
  sandbox has no Docker daemon, so containers themselves weren't started
  here — the native runs above exercise the same code paths)
