# CSR Corporate Outreach Portal

Web application to help A Ray of Hope Foundation (Pune) find, prioritize,
and track outreach to companies for CSR partnerships.

## Structure

```
CSR_Outreach_Automation/
├── backend/                    # FastAPI + PostgreSQL API (Phase 1: core application)
│   ├── app/
│   │   ├── main.py               # app entrypoint
│   │   ├── models.py             # Company, Contact, Note (SQLAlchemy)
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── crud.py               # data-access functions
│   │   └── routers/              # companies / contacts / notes endpoints
│   └── tests/                    # pytest suite
├── frontend/                   # React + Tailwind (Vite) UI
│   └── src/
│       ├── pages/                 # Companies list, Company detail
│       ├── components/            # filters, forms, contacts/notes/status panels
│       └── api/client.js          # backend API client
├── docs/                        # project docs (overview, tasks, roadmap, changelog)
├── legacy-streamlit-prototype/    # superseded early prototype — reference only, see its README
└── README.md
```

See [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) for the full
product spec, [`docs/TASKS.md`](docs/TASKS.md) for current build status,
and [`docs/ROADMAP.md`](docs/ROADMAP.md) for what's next.

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env         # then set DATABASE_URL to your PostgreSQL instance
```

`DATABASE_URL` must point at a real PostgreSQL database — a local
install, or a free managed instance (Neon / Supabase), per
[`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md)'s recommended
stack. No Docker is required or used by the app itself.

Run it:

```bash
uvicorn app.main:app --reload
```

Tables are created automatically on startup. Run the test suite (uses an
isolated in-memory SQLite database, no Postgres required for tests):

```bash
pytest -q
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies `/api/*`
requests to the backend on `http://localhost:8000` (see
`vite.config.js`). Start the backend first.
