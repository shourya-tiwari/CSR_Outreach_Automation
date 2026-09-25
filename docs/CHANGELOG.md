# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 2026-09-25

### Added — `feat: add outreach dashboard, activity feed, and CSV import/export (Phase 4)`

- New `ActivityLog` model (`backend/app/models.py`), cascade-deleted with
  its company. Written as a side effect of `crud.py`'s company/contact/
  note create + status-change logic, and by `routers/ai.py` after a
  successful email draft - no separate "log this" call needed anywhere.
- `GET /api/dashboard` (`backend/app/routers/dashboard.py`): headline
  KPI tiles (Total Companies, Contacted, Replies Received, Meetings
  Scheduled, Proposals Sent, Successful Partnerships), follow-ups
  bucketed into Overdue/Due Today/Upcoming (excludes closed-out leads),
  and the latest 20 activity-feed entries - one call for the whole
  dashboard screen. KPIs beyond raw counts read the `LeadStatus`
  pipeline in order (documented in `crud.py`) so e.g. a company at
  "Proposal Sent" still counts toward "Meetings Scheduled", without
  adding new schema just to track historical funnel stages.
- `GET /api/companies/export` / `POST /api/companies/import`
  (`backend/app/routers/companies.py`): CSV export respects the same
  filters as the company list; import reuses the existing duplicate
  check (skips rather than overwrites) and reports per-row errors
  (missing name, bad numbers) instead of failing the whole upload.
- `frontend/src/pages/DashboardPage.jsx` is now the app's landing page
  (`/`); Companies moved to `/companies`. Export/Import CSV buttons
  added to the Companies page toolbar.
- 10 new pytest cases (KPI-pipeline math, follow-up bucketing, activity
  feed ordering/cascade-delete, CSV export/import incl. duplicates and
  bad rows, activity logging on email generation); full backend suite
  now 74/74 passing. Verified live against the real dev stack (Vite
  proxy → FastAPI → SQLite). `npm run build` and `oxlint` clean.

### Added — `feat: add revenue/employee filters and pagination to company list`

- `CompanyFilters.jsx`: revenue and employee-count are now exposed in
  the UI as an optional "More filters" toggle (min/max revenue, min/max
  employees) — closes the gap where the spec's "Optional filters:
  Revenue, Employee Count" (`docs/PROJECT_OVERVIEW.md`) had no frontend
  filter UI at all, despite backend support in `search_companies`.
- `CompaniesPage.jsx`: Previous/Next pagination (25 per page) using the
  `skip`/`limit` params the backend already supported; page resets to 0
  whenever filters change.
- Verified live against the real dev stack (Vite proxy → FastAPI →
  SQLite): seeded companies with varying revenue/employee counts,
  confirmed filtering and paging return the expected slices over HTTP.
  `npm run build` and `oxlint` clean; full 64/64 backend suite still
  passing (no backend changes needed - the filter/pagination params
  already existed).

### Docs — `docs: update project docs for Phase 3 completion`

- Marked Phase 3 (AI Features) complete in `TASKS.md` and `ROADMAP.md`,
  recording the explicit provider decision (Google Gemini) and scoring
  approach (deterministic formula + LLM explanation) made with the
  user, plus verification notes.

### Added — `feat: add AI lead-score explanations, email/summary/brief generation (Phase 3)`

- `app/scoring.py`: deterministic 0-100 lead score from CSR-focus
  match, CSR spending, location match with the NGO's own city/state,
  and company size. Returned inline (`lead_score`) on every company
  list/detail response - no separate request needed. Priority label
  (High ≥70 / Medium ≥40 / Low) derived from the score.
- `app/ai.py`: Google Gemini integration (`GEMINI_API_KEY`,
  `GEMINI_MODEL`) for everything that needs an LLM - score
  explanations, email drafts, company summaries, meeting briefs. Every
  function returns `None`/reports `configured: false` when no key is
  set, same graceful-degradation pattern as Hunter/Apollo in Phase 2.
  Nothing here sends an email or takes any outreach action on its own.
- New endpoints: `POST /api/companies/{id}/score/explain`,
  `/generate-email` (First Outreach / Follow-up / Meeting Request /
  Thank You, optionally personalized to a contact), `/summary`,
  `/meeting-brief` (uses the company's saved notes as context).
- NGO profile fields (`NGO_NAME`, `NGO_WORK_AREA`, `NGO_FOCUS_AREAS`,
  `NGO_CITY`, `NGO_STATE`) added to `app/config.py`/`.env.example` -
  env-configured for now; Phase 5 will turn this into a proper profile.
- 26 new pytest cases (scoring-formula units, `ai.py` prompt/parsing
  units with mocked Gemini responses, AI-router tests incl. the
  "not configured" path); full backend suite now 64/64 passing.

### Added — `feat: add lead score, priority badges, and AI panel to frontend`

- `LeadScoreBadge.jsx`: score/priority badge on the company detail
  header with an on-demand "Why?" explanation (not auto-fetched, to
  avoid an LLM call on every page load).
- `AIPanel.jsx` (`AITextCard.jsx` + `EmailGeneratorPanel.jsx`) on the
  company detail page: Company Summary and Meeting Brief cards
  (generate/regenerate), and an email generator with a type selector,
  optional contact personalization, editable subject/body, and a Copy
  button - draft-only, no send action anywhere in the app.
- Lead Score column added to the company list table.

### Docs — `docs: update project docs for Phase 2 completion`

- Marked Phase 2 (CSR Contact Discovery) complete in `TASKS.md` and
  `ROADMAP.md`, with verification notes (test counts, the live
  robots.txt/scraping check against a local test site).

### Added — `feat: add contact discovery UI and duplicate-warning flow to frontend`

- New `DiscoverContactsPanel.jsx` on the company detail page: "Scan
  website" and "Enrich (Hunter/Apollo)" buttons surface candidate
  contacts (email/phone/LinkedIn/source), each addable to the Phase 1
  contact list after staff name them — nothing is auto-saved.
- `CompanyForm.jsx` now handles the backend's `409` duplicate response:
  shows the existing company's name with a "View existing" link and a
  "Create anyway" override that resubmits with `force=true`.
- `api/client.js`: `createCompany` accepts a `force` option; failed
  requests now carry `status` and structured `detail` on the thrown
  error so callers can branch on them; added `scrapeCompany` /
  `enrichCompany`.

### Added — `feat: add CSR contact discovery to backend (scraping, enrichment, duplicate detection)`

- `app/scraping.py`: crawls a company's own site (home, `/contact-us`,
  `/contact`, `/csr`, `/sustainability`, `/about/contact`) for public
  emails, phone numbers, and LinkedIn URLs. Identifiable User-Agent,
  `robots.txt` checked per path, fixed delay between requests, results
  deduped across pages. `POST /api/companies/{id}/scrape`.
- `app/enrichment.py`: Hunter.io domain-search and Apollo.io
  people-search integrations, filtered to CSR-relevant titles. Gated
  behind `HUNTER_API_KEY`/`APOLLO_API_KEY`; reports `configured: false`
  when neither is set rather than silently returning nothing. `POST
  /api/companies/{id}/enrich`.
- `crud.py::find_duplicate_company`: case-insensitive name match or
  normalized-website match. `POST /api/companies` now returns `409`
  with the existing company's id/name unless `?force=true` is passed.
- 25 new backend pytest cases (12 discovery-endpoint, 7 scraping unit,
  6 enrichment unit); full backend suite now 38/38 passing.

### Docs — `docs: add project docs for Phase 1`

- Added root `README.md` (setup/run instructions for both the backend
  and frontend) and a `docs/` folder (`PROJECT_OVERVIEW.md`, `TASKS.md`,
  `ROADMAP.md`, this changelog).
- Merged the old `PROJECT_OVERVIEW_V1.md` / `_V2.md` planning docs into
  `docs/PROJECT_OVERVIEW.md`, then updated it, `TASKS.md`, and
  `ROADMAP.md` to reflect Phase 1 completion on the FastAPI/PostgreSQL +
  React stack.

### Added — `feat: add React + Tailwind frontend for Phase 1 core application`

- New `frontend/` React + Tailwind (Vite) SPA: a Companies list page
  (search/filter, add-company modal, status badges) and a Company
  detail page (contacts CRUD, notes CRUD, status/follow-up editing),
  routed with `react-router-dom`. Dev server proxies `/api/*` to the
  backend on `:8000`.
- Verified: `npm run build` and `oxlint` clean; full create-company →
  add-contact → add-note → update-status → fetch-detail → filtered-list
  workflow exercised end-to-end over real HTTP through the dev proxy
  against the live backend.

### Added — `feat: add FastAPI + PostgreSQL backend for Phase 1 core application`

- New `backend/` FastAPI app: SQLAlchemy models for `Company`, `Contact`
  (many per company), and `Note`; full CRUD via `app/crud.py`; REST
  endpoints under `/api/companies`, `/api/contacts`, `/api/notes`
  (`app/routers/`). Targets PostgreSQL via `DATABASE_URL`.
- Company search endpoint with filters: name, industry, city, state,
  CSR focus, status, and CSR-spending/revenue/employee-count ranges.
- Lead status tracking (`New` → ... → `Successful`/`Not Interested`)
  plus `last_contacted_date` / `follow_up_date` on each company.
- 13 backend pytest cases (company/contact/note CRUD, filters, cascade
  delete, 404s), run against an isolated in-memory SQLite database via
  dependency override — no live Postgres required for tests.

### Changed — `chore: move legacy Streamlit prototype into legacy-streamlit-prototype/`

- Moved the earlier Streamlit/SQLite prototype (`app.py`, its `src/`
  package, `data/`, `tests/`) into `legacy-streamlit-prototype/` as a
  unit, once the new `backend/`/`frontend/` build superseded it —
  reference-only, explicitly excluded from phase-completion accounting
  per user instruction.

## 2026-09-02

### Fixed — `7ff86c8` fix: resolve module imports and safe-handle missing phone column in directory view

- Fixed `ModuleNotFoundError` by standardizing project folder structure
  and module imports (dropped the `modules/` sub-package in favor of
  top-level modules).
- Added a fallback check for the `phone` column in `app.py` to prevent a
  `KeyError` during directory rendering.
- Updated SQLite schema and migration logic to cleanly support phone
  fields.
- Split business logic out into standalone `compliance_engine.py`,
  `config.py`, `enrichment.py`, and `scraper.py` modules.
- Verified Streamlit UI rendering across the Lead Directory, Scraper,
  and Pitch Generator tabs.

### Added — `d5a48e1` feat: implement outreach dashboard, database schema, and compliance engine

- Implemented the outreach dashboard / analytics view in `app.py`.
- Expanded the SQLite database schema (`database.py`), including the
  `interaction_logs` table.
- Added the CSR compliance engine (`modules/compliance_engine.py` at
  this point in history) — CSR-1 / 80G / 12A badges and Q4 financial-year
  urgency calculation.

### Added — `b91c902` feat: Initial Prototype of website

- Initial Streamlit prototype: `app.py` and `database.py`.
- Basic company directory and SQLite persistence.
