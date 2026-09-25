# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 2026-09-25

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
