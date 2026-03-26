# Job Matcher — Strategy & Architecture Document

> Living document. Update this file as decisions are made, approaches change, or phases complete.

---

## Vision

A web application that:
1. Lets users build a rich profile (resume, skills, location, desired roles, experience, salary expectations)
2. Continuously ingests job postings from major job boards + thousands of company career pages
3. Uses semantic matching (embeddings + NLP) to surface the most relevant opportunities for each user
4. Presents ranked results with explanations, application links, and match scoring

---

## Phase Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Core user profile + DB schema + API skeleton | ✅ Complete |
| 2 | Job ingestion pipeline (job board APIs + scraping) | ✅ Complete |
| 3 | Resume/job parsing + embedding generation | ✅ Complete |
| 4 | Matching engine + ranked results API | ✅ Complete |
| 5 | Frontend web app | ✅ Complete |
| 6 | Quality, coverage & deployment readiness | ✅ Complete |
| 7 | Company career page crawler | 🔲 Not started |
| 8 | Advanced personalization & analytics | 🔲 Not started |

---

## Tech Stack

### Frontend
- **Next.js 14** (App Router) — full-stack React framework; handles routing, SSR, and API routes in one repo
- **Tailwind CSS** — utility-first styling
- **shadcn/ui** — accessible component primitives
- **React Hook Form + Zod** — form validation for profile editing

### Backend API
- **FastAPI (Python)** — async, type-safe, excellent for ML/NLP workloads
- **SQLAlchemy 2 (async)** — ORM with pgvector support
- **Pydantic v2** — request/response validation
- **Alembic** — database migrations

### Database
- **PostgreSQL 16** with **pgvector** extension
  - Stores users, profiles, jobs, embeddings, match scores all in one place
  - pgvector's `vector` column type enables cosine similarity search natively
  - Avoids the operational overhead of a separate vector DB in early phases
  - Can migrate to Weaviate/Pinecone if scale demands it

### Job Ingestion
- **python-jobspy** — battle-tested library that scrapes LinkedIn, Indeed, ZipRecruiter, Glassdoor, Google Jobs concurrently
- **Greenhouse public API** — `GET /v1/boards/{token}/jobs` returns structured JSON for thousands of tech companies
- **Lever career pages** — Lever exposes `/v0/postings/{company}` JSON endpoints (unofficial but widely used)
- **Playwright** — headless browser for company websites that use Workday, iCIMS, or custom career pages
- **Scrapy** — for large-scale company website crawls (Phase 7)

### NLP / Matching
- **spaCy** — NER for extracting skills, titles, companies, education from resumes and job descriptions
- **sentence-transformers** (`all-MiniLM-L6-v2` or `BAAI/bge-base-en-v1.5`) — open-source embeddings; no API cost
- **pgvector** `<->` operator — cosine distance search over job embeddings
- **Claude API (claude-haiku-4-5)** — optional LLM layer for match explanation and re-ranking

### Infrastructure
- **Celery + Redis** — background task queue for scheduled scraping and embedding jobs
- **Docker Compose** — local dev environment (Postgres, Redis, API, frontend, workers)
- **GitHub Actions** — CI/CD

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                      │
│  Profile Editor │ Job Feed │ Match Scores │ Apply Tracker   │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST / JSON
┌───────────────────────────▼─────────────────────────────────┐
│                     FastAPI Backend                          │
│  /users  /profile  /jobs  /matches  /scrape (trigger)       │
└──────┬────────────────────────────────────────┬─────────────┘
       │ SQLAlchemy (async)                      │ Celery tasks
┌──────▼──────────────────┐          ┌──────────▼─────────────┐
│  PostgreSQL + pgvector  │          │   Celery Workers        │
│  - users                │◄─────────│   - scrape_jobspy       │
│  - profiles             │          │   - scrape_greenhouse   │
│  - jobs (+ embedding)   │          │   - scrape_lever        │
│  - matches              │          │   - scrape_playwright   │
│  - saved_jobs           │          │   - embed_jobs          │
└─────────────────────────┘          │   - match_user          │
                                     └────────────┬────────────┘
                                                  │
                          ┌───────────────────────▼────────────┐
                          │       External Sources              │
                          │  JobSpy (LinkedIn/Indeed/etc.)      │
                          │  Greenhouse API                     │
                          │  Lever API                          │
                          │  Playwright (Workday/iCIMS/custom)  │
                          └────────────────────────────────────┘
```

---

## Database Schema (Core Tables)

```sql
-- Users & authentication
users (id, email, password_hash, created_at, updated_at)

-- Rich user profile
profiles (
  id, user_id,
  full_name, location, remote_preference,   -- REMOTE | HYBRID | ONSITE | ANY
  desired_titles TEXT[],                     -- ["Software Engineer", "Backend Developer"]
  desired_salary_min, desired_salary_max,
  years_experience,
  skills TEXT[],                             -- ["Python", "React", "AWS"]
  resume_text TEXT,                          -- raw text extracted from uploaded resume
  resume_embedding vector(384),             -- embedding of resume for similarity search
  updated_at
)

-- Scraped job postings
jobs (
  id, external_id, source,                  -- "greenhouse", "jobspy_indeed", "lever", etc.
  company, title, location, is_remote,
  salary_min, salary_max,
  description TEXT,
  embedding vector(384),                     -- embedding of job description
  url,
  posted_at, scraped_at, expires_at
)

-- Per-user match scores (computed async)
matches (
  id, user_id, job_id,
  score FLOAT,                               -- cosine similarity 0–1
  explanation TEXT,                          -- LLM-generated (optional)
  computed_at
)

-- User interactions
saved_jobs (id, user_id, job_id, saved_at)
applications (id, user_id, job_id, applied_at, status, notes)
```

---

## Job Ingestion Strategy

### Tier 1 — Official APIs (use first, most reliable)

| Source | Method | Notes |
|--------|--------|-------|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs` | Public, no auth. Thousands of tech companies. |
| Lever | `GET https://api.lever.co/v0/postings/{company}?mode=json` | Unofficial but stable. Good JSON structure. |
| ZipRecruiter | Official API | Requires account; free tier available |
| CareerBuilder | Official API | Job postings + resume search |

### Tier 2 — python-jobspy (scraping wrapper, respecting rate limits)

Scrapes: LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter
Usage: `jobs = scrape_jobs(site_name=["linkedin","indeed","glassdoor"], search_term=..., location=..., results_wanted=50)`
Rate limiting: 3–5s delay per request, proxy rotation for LinkedIn
Legal note: Violates ToS of LinkedIn/Glassdoor/Indeed. Acceptable for personal/research use; not for commercial redistribution. See legal section below.

### Tier 3 — Playwright crawls (Phase 7)

Target: Companies using Workday, iCIMS, SAP SuccessFactors, or custom career pages
Approach:
1. Maintain a list of target companies + their ATS URL pattern
2. Playwright navigates to `/careers` or `/jobs`, extracts job listings
3. Store raw HTML + extracted fields in `jobs` table

### Discovery: Building the Company List

- Curate seed list from Fortune 500, Inc 5000, tech unicorn lists
- Detect ATS type from HTML (meta tags, script src, iframe src patterns)
- Greenhouse companies: `https://boards.greenhouse.io/` directory
- Lever companies: searchable at `https://jobs.lever.co/`
- Grow list over time via user suggestions + LinkedIn company scrape

---

## Matching Engine

### Step 1 — Embedding Generation

- When a job is ingested: embed `title + company + description` → `jobs.embedding`
- When a user updates their profile: embed `resume_text + desired_titles + skills` → `profiles.resume_embedding`
- Model: `sentence-transformers/BAAI/bge-base-en-v1.5` (768-dim, fast, high quality)
- Run as Celery tasks so they don't block the API

### Step 2 — Candidate Retrieval (Fast)

```sql
SELECT j.*, 1 - (j.embedding <=> p.resume_embedding) AS score
FROM jobs j, profiles p
WHERE p.user_id = $1
  AND (j.is_remote = true OR j.location ILIKE '%' || p.location || '%')
  AND j.posted_at > NOW() - INTERVAL '30 days'
ORDER BY j.embedding <=> p.resume_embedding
LIMIT 100;
```

### Step 3 — Re-ranking (Optional, Phase 4+)

After vector retrieval, apply rule-based filters + optional LLM re-ranking:
- Hard filters: salary range, remote preference, years of experience
- Soft boost: title keyword overlap, required skills coverage
- LLM explanation: pass top 10 matches to Claude Haiku with user profile → generate 1-sentence match explanation per job

### Step 4 — Caching Results

- Store computed matches in `matches` table
- Refresh when: user updates profile OR new jobs arrive for matching titles
- Avoid re-running for every page load

---

## Resume Parsing

1. User uploads PDF/DOCX → extract text with `pdfminer.six` / `python-docx`
2. NER pass with spaCy (`en_core_web_sm` + custom pipeline):
   - Extract: job titles, companies, skills, education, dates
   - Populate `profiles.skills[]` and `profiles.desired_titles[]` as suggestions
3. Full text stored in `profiles.resume_text` for embedding
4. User can review/edit extracted fields before saving

---

## Legal & Compliance Notes

| Action | Risk Level | Mitigation |
|--------|-----------|------------|
| Greenhouse/Lever public endpoints | Low | Official/community-standard APIs |
| JobSpy scraping Indeed/LinkedIn | Medium | Personal use only; rate limit; rotate UA; honor robots.txt |
| Scraping Glassdoor | High | Avoid; they have pursued litigation |
| Storing job seeker PII | Medium | Encrypt at rest; GDPR-compliant data deletion; privacy policy |
| LinkedIn profile scraping | Very High | Do NOT scrape LinkedIn user profiles |

**Key rules:**
- Never scrape authenticated pages or bypass CAPTCHAs
- Respect `robots.txt` on all crawled domains
- Add 3–5s delays between requests; implement exponential backoff
- Do not store scraped job *applicant* data — only job *posting* data
- If productionizing commercially, migrate away from ToS-violating scrapers to licensed APIs

---

## Project File Structure

```
job-scraper/
├── STRATEGY.md                    # this file
├── docker-compose.yml             # postgres, redis, api, worker, frontend
├── .env.example
│
├── backend/                       # FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/                # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── profile.py
│   │   │   ├── job.py
│   │   │   └── match.py
│   │   ├── routers/               # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── profile.py
│   │   │   ├── jobs.py
│   │   │   └── matches.py
│   │   ├── services/
│   │   │   ├── embedding.py       # sentence-transformer wrapper
│   │   │   ├── matching.py        # vector search + re-ranking
│   │   │   ├── resume_parser.py   # PDF/DOCX + spaCy NER
│   │   │   └── scraping/
│   │   │       ├── jobspy_scraper.py
│   │   │       ├── greenhouse_scraper.py
│   │   │       ├── lever_scraper.py
│   │   │       └── playwright_scraper.py
│   │   └── tasks/                 # Celery task definitions
│   │       ├── scrape_tasks.py
│   │       └── embed_tasks.py
│   ├── alembic/                   # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      # Next.js application
│   ├── app/
│   │   ├── (auth)/login/
│   │   ├── (auth)/register/
│   │   ├── profile/               # resume upload + profile editing
│   │   ├── jobs/                  # job feed + match scores
│   │   └── saved/                 # saved jobs + application tracker
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
│
└── scripts/
    ├── seed_greenhouse_companies.py
    ├── seed_lever_companies.py
    └── backfill_embeddings.py
```

---

## Phase 1 Implementation Plan (Complete)

**Goal:** Scaffold the project, get a working API with user + profile CRUD, and a Postgres DB running locally.

Tasks:
- [ ] `docker-compose.yml` with Postgres 16 + pgvector + Redis
- [ ] FastAPI app skeleton with health check
- [ ] SQLAlchemy models: `users`, `profiles`, `jobs`, `matches`
- [ ] Alembic migrations
- [ ] Auth routes: register, login, JWT
- [ ] Profile routes: create/read/update
- [ ] Next.js app with login + profile editor pages
- [ ] `.env.example` with all required env vars

**Phase 1 does NOT include:** scraping, embeddings, or matching — those come in Phases 2–4.

---

## Phase 2 Implementation Plan (Complete)

**Goal:** Ingest real jobs into the `jobs` table.

Tasks:
- [x] Celery worker setup with Redis broker (`app/tasks/worker.py` + Beat schedule)
- [x] `greenhouse_scraper.py` — 200+ companies, polite rate limiting, retry logic
- [x] `lever_scraper.py` — 200+ companies, enriched description from lists sections
- [x] `jobspy_scraper.py` — dynamic search terms pulled from user `desired_titles` via `collect_search_terms_from_profiles()`, capped at 30
- [x] Admin router (`/admin/*`) with `X-Admin-Key` auth for manual scrape triggers + task status polling + stats
- [x] Deduplication via `UniqueConstraint(source, external_id)` + upsert in `_upsert_jobs`; re-embeds on description change
- [x] Scheduled cron: `scrape_all_sources` runs every 24h via Celery Beat

## Phase 3 Implementation Plan (Complete)

**Goal:** Generate embeddings for jobs and profiles; compute match scores.

Tasks:
- [x] Fixed `matching.py` — replaced broken `str(embedding)` SQL binding with pgvector ORM
      `cosine_distance()` operator; uses `pg_insert(...).on_conflict_do_update` for atomic upsert
- [x] Profile PATCH triggers `embed_profile` task when `desired_titles`, `skills`, or `resume_text` changes
- [x] `embed_all_jobs(batch_size)` + `embed_all_profiles()` batch tasks
- [x] `compute_all_user_matches()` task — fans out per-user `compute_user_matches` for all profiles with embeddings
- [x] Admin endpoints: `POST /admin/embed/jobs/backfill`, `POST /admin/embed/profiles/backfill`, `POST /admin/matches/recompute`
- [x] `GET /jobs/matches?min_score=0.6` — score filter added
- [x] `GET /jobs/matches/status` — tells frontend whether embedding is ready
- [x] `GET /jobs/{id}` — single job detail endpoint
- [x] `description_preview` and `explanation` (stubbed) fields on `JobResponse`
- [x] Celery Beat schedule: scrape daily → embed backfill 2h later → recompute matches 3h later
- [x] Frontend: score filter dropdown, expandable description preview, pending-embedding state

## Phase 4 Implementation Plan (Complete)

**Goal:** LLM-powered match explanations + re-ranking; search/filter UI.

Tasks:
- [x] `app/services/llm.py` — Claude Haiku wrappers: `match_explanation`, `rerank_and_explain`, `skills_gap`
      Gracefully no-ops when ANTHROPIC_API_KEY is absent
- [x] `app/tasks/llm_tasks.py` — `explain_matches_for_user`, `rerank_matches_for_user`,
      `explain_all_users`, `rerank_all_users` Celery tasks
- [x] Admin endpoints: `POST /admin/matches/explain[/{user_id}]`,
      `POST /admin/matches/rerank[/{user_id}]`
- [x] `GET /jobs/matches?title=&company=&remote=&source=&min_score=` — full filter support
- [x] `GET /jobs/search?q=&remote=` — PostgreSQL tsvector full-text search with functional GIN index
      (migration 002); attaches user's match score to search results
- [x] `GET /jobs/{id}/skills-gap` — per-job skills analysis via Claude
- [x] Frontend job detail page `/jobs/[id]` — score badge, LLM explanation, skills gap panel,
      full description preview, apply CTA
- [x] Frontend search page `/search` with full-text query + remote filter
- [x] Jobs feed: filter bar (title, company, remote, min score), cards link to detail page

## Phase 5 — Frontend Web App ✅ Complete

**Goal:** Full-featured frontend and backend for the complete user journey.

Delivered:
- [x] Auth pages: register (→ onboarding), login
- [x] 3-step onboarding wizard: resume upload → roles & skills → location & preferences
- [x] Jobs feed with filter bar (title, company, remote, min score) and "Load more" pagination
- [x] Job detail page: score badge, LLM explanation, on-demand skills gap panel
- [x] Full-text search page (`/search`)
- [x] Saved jobs page (`/saved`)
- [x] Application tracker (`/applications`): status pipeline, notes editor, summary bar
- [x] Settings page (`/settings`): change password, email notification prefs, delete account
- [x] Backend: `/applications`, `/users`, notification tasks, `send_all_digests` Celery Beat schedule
- [x] Alembic migration 003: notification columns + application status index

---

## Phase 6 — Quality, Coverage & Deployment Readiness ✅ Complete

**Goal:** Ship production-grade hardening: tests, rate limiting, prod Docker, Nginx TLS, CI.

Delivered:
- [x] Backend test suite: 37 tests across auth, profile, jobs, applications (`pytest` + `httpx.AsyncClient`)
  - Isolated per-test DB state via function-scoped engine fixtures
  - Rate-limiter storage reset between tests; Celery tasks mocked
  - Fixed `bcrypt==4.2.1` pin (bcrypt 5.x broke passlib 1.7.4 compat)
- [x] Rate limiting via `slowapi`: 5/min on `/auth/register`, 10/min on `/auth/login`
- [x] `app/limiter.py` singleton — avoids circular import between `main.py` and `auth.py`
- [x] `app_env` config field (`development` | `production`): tightens CORS, hides `/docs` in prod
- [x] `backend/scripts/start.sh`: runs `alembic upgrade head` then starts uvicorn (or gunicorn in prod)
- [x] `backend/Dockerfile`: now sets `CMD ["/app/scripts/start.sh"]`
- [x] `frontend/Dockerfile`: multi-stage build (node:20-alpine builder → runner)
- [x] `nginx/nginx.conf`: Nginx reverse proxy with TLS, HTTP→HTTPS redirect, security headers, Certbot integration
- [x] `docker-compose.prod.yml`: 7 services (postgres, redis, api, worker, beat, frontend, nginx + certbot); gunicorn 4 workers; separate beat scheduler
- [x] `.github/workflows/ci.yml`: lint (ruff) → test (postgres+redis services) → build+push Docker to GHCR on main
- [x] `backend/requirements-dev.txt`: pytest + pytest-asyncio + httpx + ruff
- [x] `backend/pyproject.toml`: pytest config (`asyncio_mode = "auto"`)

---

## Phase 7 Implementation Plan (Next)

**Goal:** Company career page crawler for direct sourcing from 1000+ company sites.

Tasks:
- [ ] Build a company registry: CSV/DB table of `(company_name, careers_url, ats_type)` with 500+ seed entries
- [ ] ATS type detector: inspect HTML for Workday/iCIMS/Greenhouse/Lever/Taleo fingerprints
- [ ] Playwright scraper for **Workday** (`myworkdayjobs.com` domains): navigate to `/en-US/External`, extract job cards
- [ ] Playwright scraper for **iCIMS** (career portals ending in `.icims.com`): list page + job detail extraction
- [ ] Generic fallback scraper: XPath/CSS heuristics for custom career pages
- [ ] Deduplication against existing Greenhouse/Lever jobs (match on `company` + `title` + ~`posted_at`)
- [ ] Rate limiting: ≥5s between requests per domain, 30s timeout, exponential backoff on 429/503
- [ ] New Celery task `scrape_company_careers(company_id)` + `scrape_all_company_careers()` fan-out
- [ ] Admin endpoint `POST /admin/scrape/companies` to trigger manually
- [ ] `robots.txt` checker utility before scraping any URL

---

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-26 | PostgreSQL + pgvector over dedicated vector DB | Simpler ops; handles 10M+ vectors; can always migrate |
| 2026-03-26 | FastAPI (Python) over Node.js backend | Python ecosystem for NLP (spaCy, sentence-transformers, pdfminer) is far superior |
| 2026-03-26 | sentence-transformers (local) over OpenAI embeddings | No per-token cost; runs in Celery worker; good enough quality |
| 2026-03-26 | python-jobspy for scraping | Purpose-built, maintained, handles anti-bot measures better than raw scrapers |
| 2026-03-26 | Next.js for frontend | Full-stack in one framework; file-based routing; easy API proxying |
