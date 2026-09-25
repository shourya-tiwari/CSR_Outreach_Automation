# Tasks

Status against the phased plan in [`ROADMAP.md`](ROADMAP.md), as of
2026-09-25. **The `legacy-streamlit-prototype/` code does not count
toward any phase's completion** (explicit user instruction) — all
status below reflects only `backend/` (FastAPI + PostgreSQL) and
`frontend/` (React + Tailwind). Legend: ✅ done · 🟡 partial · ⬜ not
started.

## Phase 1 — Core Application — ✅ Complete

- [x] **Database** — PostgreSQL via SQLAlchemy (`backend/app/models.py`):
      `companies`, `contacts` (many per company), `notes`. Tables are
      created automatically on app startup.
- [x] **Web interface** — React + Tailwind (Vite) SPA: a Companies list
      page and a Company detail page, routed with `react-router-dom`.
- [x] **Company search** — filter by name, industry, city, state,
      CSR focus, status, and CSR-spending/revenue/employee-count ranges
      (`GET /api/companies`, `backend/app/crud.py::search_companies`).
- [x] **Company profile page** — `frontend/src/pages/CompanyDetailPage.jsx`:
      company info, CSR focus/spending/revenue/employee stats, contacts,
      notes, and outreach status — all in one view.
- [x] **Contact database** — first-class `Contact` model, many per
      company, full CRUD (add/edit/delete) via
      `frontend/src/components/ContactsSection.jsx` and
      `/api/companies/{id}/contacts`, `/api/contacts/{id}`.
- [x] **Notes and status tracking** — freeform `Note`s per company
      (`NotesSection.jsx`) plus a `status` (lead stage enum),
      `last_contacted_date`, and `follow_up_date` on each company,
      editable via `StatusPanel.jsx` / `PATCH /api/companies/{id}`.

**Verified:** 13/13 backend pytest cases passing (company CRUD/search,
contact CRUD, note CRUD, cascade delete, 404 handling); `npm run build`
and `oxlint` clean on the frontend; full create-company → add-contact →
add-note → update-status → fetch-detail → filtered-list workflow
exercised end-to-end through the real dev stack (Vite proxy → FastAPI →
DB) via HTTP, matching exactly what the UI calls.

**Known gaps vs. the six-feature MVP** (intentionally out of Phase 1
scope, tracked for later phases): revenue/employee-count are stored and
filterable but not yet shown as *optional* toggle filters in the UI
(they're always-visible fields); no pagination on the company list yet
(fine at prototype scale, `skip`/`limit` are already supported
server-side).

## Phase 2 — CSR Contact Discovery — ⬜ Not started

Web scraping (`/csr`, `/sustainability`, `/contact-us` crawling),
Hunter/Apollo enrichment, and duplicate detection need to be rebuilt
against the new backend — none of this exists in `backend/` yet. (A
scraper and enrichment module exist in `legacy-streamlit-prototype/`,
but per instruction they aren't credited here — this phase starts from
zero against the new stack.)

## Phase 3 — AI Features — ⬜ Not started

No lead scoring or email generation exists in `backend/`/`frontend/`
yet.

## Phase 4 — Outreach Tracking — ⬜ Not started

No dashboard/analytics view, KPI tiles, or activity feed exists yet.
Status/follow-up-date tracking (Phase 1) is the foundation this will
build on.

## Phase 5 — MVP+ Features — ⬜ Not started

NGO Profile, document storage, tags, proposal tracker, activity
timeline — none started.

## Phase 6 — Final Testing & Deployment — ⬜ Not started

---

## Near-Term Engineering Tasks

- [ ] Add pagination controls to the company list UI (backend already
      supports `skip`/`limit`).
- [ ] Consider Alembic migrations once the schema needs to evolve after
      real data exists (Phase 1 uses `Base.metadata.create_all` for
      simplicity, matching the "avoid infra complexity" principle).
- [ ] Add duplicate-detection at create time (currently absent — was
      explicitly scoped to Phase 2 in the plan, not Phase 1).
- [ ] Decide on auth before this goes anywhere multi-user (Phase 1 has
      none — fine for a single NGO's internal tool for now).

See [`ROADMAP.md`](ROADMAP.md) for how these fit into upcoming phases and
[`CHANGELOG.md`](CHANGELOG.md) for what's already shipped.
