"""Phase 6: larger-volume sanity check.

Seeds a realistically messy set of companies (varied industries/cities/
statuses, most with a couple of contacts/notes, a fraction tagged) into a
file-backed SQLite database, then times the actual HTTP endpoints the UI
calls against that data - list/search/filter/paginate, CSV export, the
dashboard, and a single company's full detail view.

Caveat: this runs against SQLite, not the production PostgreSQL target
(see docs/PROJECT_OVERVIEW.md) - there's no live Postgres instance in this
environment to test against. SQLite is a reasonable proxy for "does
anything fall over or get obviously slow at this row count", not a
substitute for re-running this against real Postgres before launch.

Usage:
    python scripts/load_test.py [--companies 3000]
"""

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud, models, schemas
from app.database import Base, get_db
from app.main import app

INDUSTRIES = ["Manufacturing", "Technology", "Healthcare", "Retail", "Finance", "Energy", "Textiles"]
CITIES = [
    ("Pune", "Maharashtra"),
    ("Mumbai", "Maharashtra"),
    ("Bangalore", "Karnataka"),
    ("Delhi", "Delhi"),
    ("Chennai", "Tamil Nadu"),
    ("Hyderabad", "Telangana"),
]
CSR_FOCUS = ["Education", "Healthcare", "Environment", "Rural Development", "Women Empowerment"]
STATUSES = list(crud.models.LeadStatus)
TAGS = ["High Priority", "Education", "Follow-up Q1", "Pune", "Renewed Interest"]


def seed(db, n: int) -> None:
    """Inserts directly via the ORM (bypassing crud's per-record commits,
    which are fine for real usage but far too slow for seeding thousands
    of rows at once) and commits in batches instead.
    """
    tags = {name: models.Tag(name=name) for name in TAGS}
    db.add_all(tags.values())
    db.flush()

    for i in range(n):
        city, state = random.choice(CITIES)
        company = models.Company(
            name=f"Company {i:05d}",
            industry=random.choice(INDUSTRIES),
            city=city,
            state=state,
            website=f"https://company{i:05d}.example.com",
            csr_focus=random.choice(CSR_FOCUS),
            csr_spending=random.uniform(50_000, 20_000_000),
            revenue=random.uniform(1_000_000, 5_000_000_000),
            employee_count=random.randint(10, 20_000),
            status=random.choice(STATUSES),
        )
        db.add(company)
        db.flush()  # assign company.id without a full commit

        for c in range(random.randint(0, 3)):
            db.add(
                models.Contact(
                    company_id=company.id, name=f"Contact {i}-{c}", designation="CSR Head"
                )
            )
        if i % 4 == 0:
            db.add(models.Note(company_id=company.id, body=f"Note about company {i}"))
        if i % 10 == 0:
            company.tags.append(tags[random.choice(TAGS)])

        if i % 500 == 0 and i:
            db.commit()
            print(f"  seeded {i}...", flush=True)
    db.commit()


def timed(label, fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"{label:<45} {elapsed_ms:8.1f} ms")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies", type=int, default=3000)
    parser.add_argument("--db-file", default="load_test.db")
    args = parser.parse_args()

    db_path = Path(__file__).resolve().parent / args.db_file
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    print(f"Seeding {args.companies} companies...")
    seed_db = TestingSessionLocal()
    start = time.perf_counter()
    seed(seed_db, args.companies)
    seed_db.close()
    print(f"Seed complete in {time.perf_counter() - start:.1f}s\n")

    print(f"{'Endpoint':<45} {'Time':>10}")
    print("-" * 57)
    timed("GET /api/companies (default page)", lambda: client.get("/api/companies"))
    timed(
        "GET /api/companies?limit=500",
        lambda: client.get("/api/companies", params={"limit": 500}),
    )
    timed(
        "GET /api/companies (name filter, ilike)",
        lambda: client.get("/api/companies", params={"name": "Company 019"}),
    )
    timed(
        "GET /api/companies (combined filters)",
        lambda: client.get(
            "/api/companies",
            params={"industry": "Technology", "city": "Pune", "min_csr_spending": 1_000_000},
        ),
    )
    timed(
        "GET /api/companies?tag=Education",
        lambda: client.get("/api/companies", params={"tag": "Education"}),
    )
    timed(
        "GET /api/companies (deep pagination, skip=2900)",
        lambda: client.get("/api/companies", params={"skip": max(args.companies - 100, 0), "limit": 100}),
    )
    timed("GET /api/companies/export (full CSV)", lambda: client.get("/api/companies/export"))
    timed("GET /api/dashboard", lambda: client.get("/api/dashboard"))
    timed("GET /api/companies/1 (single detail)", lambda: client.get("/api/companies/1"))

    app.dependency_overrides.clear()
    engine.dispose()
    db_path.unlink()


if __name__ == "__main__":
    main()
