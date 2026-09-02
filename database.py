"""
database.py
------------
SQLite data-access layer for A Ray of Hope Foundation's
CSR Corporate Outreach & Lead Tracker.

Backing store: SQLite (file path configured via config.DB_PATH,
defaults to csr_tracker.db)
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import pandas as pd

from config import DB_PATH, LEAD_STATUSES, STATUS_WIN_PROBABILITY


# ----------------------------------------------------------------------------
# CONNECTION HELPERS
# ----------------------------------------------------------------------------
@contextmanager
def get_connection():
    """Context-managed SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# SCHEMA SETUP
# ----------------------------------------------------------------------------
def init_db() -> None:
    """Create tables and indexes if they do not already exist."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name        TEXT NOT NULL,
                zone                TEXT NOT NULL,
                csr_focus           TEXT,
                contact_person      TEXT,
                designation         TEXT,
                email               TEXT,
                phone               TEXT,
                linkedin_url        TEXT,
                csr_budget_lakhs    REAL,
                target_grant_lakhs  REAL,
                win_probability     REAL DEFAULT 0.20,
                last_contacted_date TEXT,
                financial_year      TEXT,
                status              TEXT DEFAULT 'New Lead',
                last_notes          TEXT,
                created_at          TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS interaction_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id  INTEGER NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                action      TEXT NOT NULL,
                notes       TEXT,
                FOREIGN KEY (company_id) REFERENCES companies (id)
                    ON DELETE CASCADE
            )
            """
        )

        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_zone ON companies(zone)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_company_id ON interaction_logs(company_id)"
        )


# ----------------------------------------------------------------------------
# CORE CRUD HELPERS
# ----------------------------------------------------------------------------
def get_all_companies() -> List[Dict[str, Any]]:
    """Return every company row as a list of dicts, most recent first."""
    init_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]


def get_all_companies_df() -> pd.DataFrame:
    """Convenience wrapper returning companies as a pandas DataFrame."""
    rows = get_all_companies()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id", "company_name", "zone", "csr_focus", "contact_person",
                "designation", "email", "phone", "linkedin_url",
                "csr_budget_lakhs", "target_grant_lakhs", "win_probability",
                "last_contacted_date", "financial_year", "status",
                "last_notes", "created_at",
            ]
        )
    return pd.DataFrame(rows)


def get_company_by_id(company_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def add_company(
    company_name: str,
    zone: str,
    csr_focus: str,
    contact_person: str,
    designation: str,
    email: str,
    phone: str = "",
    linkedin_url: str = "",
    status: str = "New Lead",
    notes: str = "",
    csr_budget_lakhs: Optional[float] = None,
    target_grant_lakhs: Optional[float] = None,
    win_probability: Optional[float] = None,
    financial_year: str = "FY25-26",
) -> int:
    """Insert a new company record. Returns the new row's id."""
    init_db()

    if win_probability is None:
        win_probability = STATUS_WIN_PROBABILITY.get(status, 0.20)

    if status not in LEAD_STATUSES:
        status = "New Lead"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO companies (
                company_name, zone, csr_focus, contact_person, designation,
                email, phone, linkedin_url, csr_budget_lakhs, target_grant_lakhs,
                win_probability, last_contacted_date, financial_year,
                status, last_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name, zone, csr_focus, contact_person, designation,
                email, phone, linkedin_url, csr_budget_lakhs, target_grant_lakhs,
                win_probability, None, financial_year, status, notes,
            ),
        )
        new_id = cur.lastrowid

    log_interaction(new_id, "Lead Created", f"Initial status: {status}")
    return new_id


def update_company_status(company_id: int, new_status: str, notes: str = "") -> None:
    """Update a company's status/notes, refresh its win probability, and log the change."""
    if new_status not in LEAD_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    new_win_probability = STATUS_WIN_PROBABILITY.get(new_status, 0.20)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE companies
            SET status = ?,
                last_notes = ?,
                win_probability = ?,
                last_contacted_date = ?
            WHERE id = ?
            """,
            (new_status, notes, new_win_probability, date.today().isoformat(), company_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"No company found with id={company_id}")

    log_interaction(company_id, f"Status changed to '{new_status}'", notes)


def update_company(company_id: int, **fields) -> None:
    """Generic partial-update for any subset of editable columns."""
    if not fields:
        return

    allowed_cols = {
        "company_name", "zone", "csr_focus", "contact_person", "designation",
        "email", "phone", "linkedin_url", "csr_budget_lakhs",
        "target_grant_lakhs", "win_probability", "last_contacted_date",
        "financial_year", "status", "last_notes",
    }
    updates = {k: v for k, v in fields.items() if k in allowed_cols}
    if not updates:
        return

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [company_id]

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
        if cur.rowcount == 0:
            raise ValueError(f"No company found with id={company_id}")

    log_interaction(company_id, "Record Updated", f"Fields changed: {list(updates.keys())}")


def delete_company(company_id: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        if cur.rowcount == 0:
            raise ValueError(f"No company found with id={company_id}")


# ----------------------------------------------------------------------------
# INTERACTION LOG HELPERS
# ----------------------------------------------------------------------------
def log_interaction(company_id: int, action: str, notes: str = "") -> int:
    """Append a row to interaction_logs. Returns the new log id."""
    init_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO interaction_logs (company_id, timestamp, action, notes)
            VALUES (?, ?, ?, ?)
            """,
            (company_id, datetime.now().isoformat(timespec="seconds"), action, notes),
        )
        return cur.lastrowid


def get_interaction_history(company_id: int) -> List[Dict[str, Any]]:
    """Return all interaction log rows for a company, most recent first."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM interaction_logs
            WHERE company_id = ?
            ORDER BY timestamp DESC
            """,
            (company_id,),
        )
        return [dict(row) for row in cur.fetchall()]


# ----------------------------------------------------------------------------
# BULK IMPORT (CSV UPLOAD)
# ----------------------------------------------------------------------------
REQUIRED_BULK_COLUMNS = [
    "company_name", "zone", "csr_focus", "contact_person",
    "designation", "email",
]

OPTIONAL_BULK_COLUMNS = [
    "phone", "linkedin_url", "csr_budget_lakhs", "target_grant_lakhs",
    "win_probability", "financial_year", "status", "last_notes",
]


def bulk_insert_companies(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Bulk-insert companies from a DataFrame (e.g. an uploaded CSV).

    Required columns: company_name, zone, csr_focus, contact_person,
    designation, email.
    Optional columns: phone, linkedin_url, csr_budget_lakhs,
    target_grant_lakhs, win_probability, financial_year, status, last_notes.

    Returns a summary dict: {"inserted": int, "skipped": int, "errors": [...]}.
    """
    init_db()

    missing_cols = [c for c in REQUIRED_BULK_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    inserted = 0
    skipped = 0
    errors: List[str] = []

    with get_connection() as conn:
        cur = conn.cursor()
        for idx, row in df.iterrows():
            try:
                company_name = str(row.get("company_name", "")).strip()
                if not company_name:
                    skipped += 1
                    continue

                status = row.get("status", "New Lead")
                if status not in LEAD_STATUSES:
                    status = "New Lead"

                win_probability = row.get("win_probability")
                needs_default = win_probability is None or (
                    isinstance(win_probability, float) and pd.isna(win_probability)
                )
                if needs_default:
                    win_probability = STATUS_WIN_PROBABILITY.get(status, 0.20)

                cur.execute(
                    """
                    INSERT INTO companies (
                        company_name, zone, csr_focus, contact_person,
                        designation, email, phone, linkedin_url,
                        csr_budget_lakhs, target_grant_lakhs, win_probability,
                        last_contacted_date, financial_year, status, last_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        company_name,
                        row.get("zone"),
                        row.get("csr_focus"),
                        row.get("contact_person"),
                        row.get("designation"),
                        row.get("email"),
                        row.get("phone", ""),
                        row.get("linkedin_url", ""),
                        row.get("csr_budget_lakhs"),
                        row.get("target_grant_lakhs"),
                        win_probability,
                        None,
                        row.get("financial_year", "FY25-26"),
                        status,
                        row.get("last_notes", ""),
                    ),
                )
                new_id = cur.lastrowid
                cur.execute(
                    """
                    INSERT INTO interaction_logs (company_id, timestamp, action, notes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        datetime.now().isoformat(timespec="seconds"),
                        "Lead Created (Bulk Import)",
                        "Imported via CSV upload",
                    ),
                )
                inserted += 1
            except Exception as e:
                skipped += 1
                errors.append(f"Row {idx}: {e}")

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


# ----------------------------------------------------------------------------
# MODULE INIT
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")