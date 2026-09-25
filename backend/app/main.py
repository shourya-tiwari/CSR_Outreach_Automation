"""FastAPI entrypoint for the CSR Outreach backend (Phase 1: core application)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401 - import registers models on Base.metadata
from .config import settings
from .database import Base, engine
from .routers import companies, contacts, notes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Deferred to app startup (not import time) so importing this module
    # for testing doesn't require a live database connection - tests
    # supply their own engine via dependency override (see tests/conftest.py).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="CSR Outreach Portal API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(contacts.router)
app.include_router(notes.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
