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

**Update (2026-09-25):** revenue/employee-count are now exposed in the
UI as an *optional* "More filters" toggle in `CompanyFilters.jsx` (per
the spec's "Optional filters: Revenue, Employee Count"), and the company
list has Previous/Next pagination (`CompaniesPage.jsx`, 25 per page)
using the `skip`/`limit` params `search_companies` already supported.
Verified live against the real dev stack (Vite proxy → FastAPI →
SQLite): seeded companies with varying revenue/employee counts,
confirmed `min_revenue`/`max_revenue`/`min_employees`/`max_employees`
filtering and `skip`/`limit` paging return the expected slices over
HTTP. `npm run build` and `oxlint` clean.

## Phase 2 — CSR Contact Discovery — ✅ Complete

- [x] **CSR decision-maker search** — `backend/app/scraping.py`:
      crawls a company's own site (`/`, `/contact-us`, `/contact`,
      `/csr`, `/sustainability`, `/about/contact`) for public emails,
      phone numbers, and LinkedIn URLs. Identifiable User-Agent,
      `robots.txt` checked per path before fetching, fixed delay
      between requests, results deduped across pages.
- [x] **Source-link tracking** — every discovered candidate carries the
      `source_url` it was found on (`Contact.source_url` was already
      modeled in Phase 1).
- [x] **Save discovered contacts** — `frontend/src/components/
      DiscoverContactsPanel.jsx` on the company detail page: "Scan
      website" shows candidates, staff name each one and click "Add
      contact" to save via the existing Phase 1 contact endpoint —
      nothing is auto-saved without review.
- [x] **Duplicate detection** — `backend/app/crud.py::find_duplicate_company`
      (case-insensitive name match or normalized-website match).
      `POST /api/companies` returns `409` with the existing company's
      id/name unless `?force=true` is passed; the "Add company" form
      surfaces this as a warning with a "View existing" link and a
      "Create anyway" override.
- [x] **Hunter.io / Apollo.io enrichment** — `backend/app/enrichment.py`:
      domain-search/people-search integrations, filtered to CSR-relevant
      titles (CSR/Sustainability/Foundation/HR/Corporate Communications).
      Gated behind `HUNTER_API_KEY`/`APOLLO_API_KEY`; `POST
      /api/companies/{id}/enrich` reports `configured: false` when
      neither key is set, surfaced in the UI rather than silently
      returning nothing. Same `DiscoverContactsPanel.jsx` UI as
      scraping.

**Verified:** 25 new backend pytest cases (12 discovery-endpoint tests,
7 scraping unit tests, 6 enrichment unit tests — 38 total for the
backend now) — all passing. The scraper was also run against a live,
locally-hosted test site with real contact content on one page and a
`robots.txt` `Disallow` rule on another, confirming the disallowed page
was genuinely skipped (not just coincidentally empty) while the allowed
pages' emails/phone/LinkedIn were correctly extracted. Duplicate
detection, scrape, and enrich were all exercised over real HTTP through
the dev proxy. `npm run build` and `oxlint` clean on the frontend.

## Phase 3 — AI Features — ✅ Complete

Provider decision (made explicitly with the user, not drifted into):
**Google Gemini**, and lead scoring is a **deterministic formula +
LLM-written explanation** — the 0-100 number is fixed/auditable
(`backend/app/scoring.py`), the LLM only writes the human-readable
"why" text. All AI calls are optional: every endpoint reports
`configured: false` when `GEMINI_API_KEY` isn't set rather than
erroring, same pattern as Hunter/Apollo in Phase 2.

- [x] **AI lead scoring** — `backend/app/scoring.py::compute_lead_score`:
      0-100 score from CSR-focus match (0-40), CSR spending (0-30),
      location match with the NGO's own city/state (0-15), and company
      size (0-15) — factors from `docs/PROJECT_OVERVIEW.md` that map to
      data actually on the `Company` record. Returned inline on every
      `GET/POST/PATCH /api/companies...` response (list and detail) —
      no configuration or extra request needed, matching "should
      automatically appear on every company profile."
- [x] **Lead priority labels** — High (≥70) / Medium (≥40) / Low,
      derived from the score, shown as a colored badge on both the
      company list and detail page.
- [x] **Score explanation** — `POST /api/companies/{id}/score/explain`:
      Gemini writes 2-3 plain-language bullets from the score
      breakdown. Lazy (on-demand "Why?" click), not fetched
      automatically, to avoid an LLM call on every page load.
- [x] **AI email generator** — `POST /api/companies/{id}/generate-email`:
      First Outreach / Follow-up / Meeting Request / Thank You variants,
      optionally personalized to a specific contact. Draft-only per the
      plan's rule — the UI has Generate/Regenerate/Copy buttons and an
      editable subject/body, no send action exists anywhere in the app.
- [x] **AI Company Summary** — `POST /api/companies/{id}/summary`:
      business overview, CSR initiatives, NGO-fit, talking points.
- [x] **AI Meeting Brief** — `POST /api/companies/{id}/meeting-brief`:
      background, likely priorities, discussion points, questions,
      collaboration ideas — includes the company's saved notes as
      context.

**Verified:** 26 new backend pytest cases (scoring formula unit tests,
`app/ai.py` prompt/parsing unit tests with mocked Gemini responses,
router tests for all 4 AI endpoints including the "not configured"
path — 64 total for the backend now) — all passing. Also called the
real Gemini API once with a deliberately invalid key to confirm the
request reaches Google's endpoint and a failure is caught and returned
as `None` rather than crashing (no valid `GEMINI_API_KEY` was available
to test an actual successful generation — that path is covered by the
mocked unit/router tests instead). Full create-company → lead-score →
explain/generate-email/summary/meeting-brief (all correctly reporting
`configured: false`) workflow replayed over real HTTP through the dev
proxy. `npm run build` and `oxlint` clean on the frontend.

**Known gap:** "Previous CSR activities" (the *target* company's own
CSR track record) was in the original factor list but isn't scored —
no structured data source for that is integrated (would need e.g. Form
CSR-2 filings or annual reports), so it's left out rather than faked.

## Phase 4 — Outreach Tracking — ✅ Complete

- [x] **Dashboard view with headline KPI tiles** — `GET /api/dashboard`
      (`backend/app/routers/dashboard.py`) returns Total Companies,
      Companies Contacted, Replies Received, Meetings Scheduled,
      Proposals Sent, and Successful Partnerships in one call, rendered
      on `frontend/src/pages/DashboardPage.jsx` (now the app's landing
      page, `/`). KPIs beyond "current status" use a documented ordered
      reading of the `LeadStatus` pipeline (`crud.py`'s
      `_REPLIED_OR_LATER`/`_MEETING_OR_LATER`/`_PROPOSAL_OR_LATER`) so a
      company at e.g. "Proposal Sent" still counts toward "Meetings
      Scheduled" — a lighter-weight substitute for full historical
      funnel tracking, deliberately chosen over adding more schema.
- [x] **Follow-up section** — same endpoint buckets every company with a
      `follow_up_date` into Overdue / Due Today / Upcoming
      (`crud.py::get_follow_ups`), excluding closed-out leads
      (Successful / Not Interested) since a reminder on a closed deal
      isn't actionable. Shown as three columns on the dashboard.
- [x] **Recent-activity feed** — new `ActivityLog` model
      (`backend/app/models.py`), written as a side effect of
      `crud.py`'s create/update functions (company added, contact
      added/updated, note added, status changed) and of a successful AI
      email generation (`routers/ai.py`). `GET /api/dashboard` returns
      the latest 20 system-wide, newest first; cascade-deletes with its
      company.
- [x] **CSV import/export** — `GET /api/companies/export` (respects the
      same filters as the company list) and `POST
      /api/companies/import` (`backend/app/routers/companies.py`,
      `crud.py::import_companies_from_rows`) on the Companies page.
      Import skips name/website duplicates via the existing
      `find_duplicate_company` check and reports per-row errors
      (missing name, unparseable numbers) rather than failing the whole
      upload.

**Verified:** 10 new backend pytest cases (KPI-pipeline math, follow-up
bucketing incl. today's real date via `date.today()`, activity-feed
ordering and cascade-delete, CSV export/import incl. duplicate-skip and
bad-row reporting, activity logging on email generation — 74 total for
the backend now) — all passing. Also exercised live against the real
dev stack (Vite proxy → FastAPI → SQLite): seeded companies across
different statuses/follow-up dates, confirmed dashboard KPIs/follow-up
buckets/activity feed, CSV export, and CSV import (create + duplicate
skip + bad-row report) all return correct results over HTTP matching
what the UI calls. `npm run build` and `oxlint` clean on the frontend.

## Phase 5 — MVP+ Features — ✅ Complete

- [x] **NGO Profile** — new single-row `NGOProfile` model
      (`backend/app/models.py`), replacing the env-only `NGO_*` settings
      as the thing NGO staff actually edit. `GET/PATCH /api/ngo-profile`
      (`routers/ngo_profile.py`); `frontend/src/pages/NGOProfilePage.jsx`
      (`/ngo-profile`, linked from the nav). Seeded from the existing env
      defaults on first access; every read/write mirrors the row onto
      the live `settings` object (`crud.py`'s
      `_sync_settings_from_ngo_profile`) so `scoring.py`'s
      location/focus match and `ai.py`'s generated content pick up edits
      immediately, without threading a db session through either module.
      Re-synced from the DB on app startup so edits survive a restart.
- [x] **Tags** — new `Tag` model + `company_tags` association table
      (many-to-many, reusable across companies). `GET/POST /api/tags`,
      `DELETE /api/tags/{id}` (`routers/tags.py`); attach/detach via
      `POST/DELETE /api/companies/{id}/tags[/​{tag_id}]`
      (`routers/companies.py`), get-or-create by case-insensitive name
      so re-adding "education" reuses "Education" rather than
      duplicating. `search_companies` gained a `tag` filter, surfaced as
      a dropdown in `CompanyFilters.jsx`; tags shown as chips on both
      the company list and detail page (`TagsSection.jsx`).
- [x] **Document storage** — new `Document` model, file bytes stored
      directly in Postgres (`LargeBinary`, deferred-loaded so listing
      documents doesn't pull file contents into memory) rather than
      standing up separate file-storage infra. `POST
      /{company_id}/documents` (upload), `GET /api/documents/{id}`
      (download, streamed), `DELETE /api/documents/{id}`
      (`routers/documents.py`); `DocumentsSection.jsx` on the company
      detail page.
- [x] **Proposal Tracker** — new `Proposal` model with its own stage
      enum (Requested → Drafting → Sent → Approved/Rejected), separate
      from the company's overall lead `status` since a company can have
      several proposals over time. `POST /{company_id}/proposals`,
      `PATCH/DELETE /api/proposals/{id}` (`routers/proposals.py`);
      `ProposalsSection.jsx` (add + inline stage dropdown) on the
      company detail page. Stage changes are activity-logged.
- [x] **Activity Timeline** — `CompanyDetail` now embeds that company's
      own `activity_logs` (full history, not just the dashboard's
      system-wide latest-20), rendered as `ActivityTimeline.jsx` on the
      company detail page. Fixed a same-second ordering bug found while
      verifying this live: SQLite/Postgres `created_at` ties (multiple
      events in the same second, common when several actions fire back
      to back) weren't deterministically newest-first without a
      secondary `id DESC` sort key - added to both the `ActivityLog`
      relationship ordering and `crud.get_recent_activity`.

**Verified:** 21 new backend pytest cases (tags incl. case-insensitive
reuse and company filtering, document upload/download/delete incl.
cascade-delete with the company, proposal CRUD and stage-change activity
logging, NGO profile seed/update/settings-sync incl. its effect on live
lead scoring — 95 total for the backend now) — all passing. Also
exercised live against the real dev stack (Vite proxy → FastAPI →
SQLite): tag create/attach/detach/filter, document upload+download with
byte-for-byte content verification, proposal stage transitions, and NGO
profile edits changing a newly-created company's lead score, all
confirmed over real HTTP. `npm run build` and `oxlint` clean on the
frontend.

## Phase 6 — Final Testing & Deployment — ⬜ Not started

---

## Near-Term Engineering Tasks

- [x] Add pagination controls to the company list UI (backend already
      supports `skip`/`limit`) — done 2026-09-25.
- [ ] Consider Alembic migrations once the schema needs to evolve after
      real data exists (Phase 1 uses `Base.metadata.create_all` for
      simplicity, matching the "avoid infra complexity" principle).
- [ ] Decide on auth before this goes anywhere multi-user (Phase 1 has
      none — fine for a single NGO's internal tool for now).
- [ ] Scraper title/name extraction is currently heuristic-free: emails,
      phones, and LinkedIn URLs are found, but not a person's name or
      designation (staff fill that in before saving). Named-contact
      extraction would need real HTML structure/NLP parsing, not just
      regex — deliberately out of scope for Phase 2's MVP.

See [`ROADMAP.md`](ROADMAP.md) for how these fit into upcoming phases and
[`CHANGELOG.md`](CHANGELOG.md) for what's already shipped.
