"""
database.py
------------
Production data-access layer for A Ray of Hope Foundation's
CSR Corporate Outreach & Lead Tracker.

Backing store: SQLite (file: csr_tracker.db)
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import pandas as pd

DB_PATH = "csr_tracker.db"


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
def init_db():
    """Create tables if they do not already exist."""
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
                linkedin_url        TEXT,
                csr_budget_lakhs    REAL,
                target_grant_lakhs  REAL,
                win_probability     REAL DEFAULT 0.20,
                last_contacted_date TEXT,
                financial_year      TEXT,
                status              TEXT DEFAULT 'New Lead',
                last_notes          TEXT
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

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_companies_zone ON companies(zone)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_company_id "
            "ON interaction_logs(company_id)"
        )


# ----------------------------------------------------------------------------
# SEED DATA
# ----------------------------------------------------------------------------
def seed_data(force: bool = False):
    """
    Populate `companies` with verified contact records for Pune corporates.

    Args:
        force: if True, wipes existing rows before reseeding.
    """
    init_db()

    with get_connection() as conn:
        cur = conn.cursor()

        if force:
            cur.execute("DELETE FROM interaction_logs")
            cur.execute("DELETE FROM companies")

        cur.execute("SELECT COUNT(*) AS cnt FROM companies")
        if cur.fetchone()["cnt"] > 0 and not force:
            return  # already seeded

        seed_rows = [
            (
                "Bharat Forge Ltd", "Chakan", "Skill Development & Primary Education",
                "Tejaswini Chaudhari", "Company Secretary & Compliance Officer",
                "tejaswini.chaudhari@bharatforge.com", "https://www.linkedin.com/company/bharat-forge/",
                700.0, 15.0, 0.20, None, "FY25-26", "New Lead",
                "Public CSR policy names primary education and skill development as core focus areas.",
            ),
            (
                "Infosys Ltd", "Hinjawadi Phase 1", "Digital Education (Infosys Springboard)",
                "Infosys Foundation Desk", "CSR Program Manager",
                "foundation@infosys.com", "https://www.linkedin.com/company/infosys/",
                350.0, 20.0, 0.20, None, "FY25-26", "New Lead",
                "Infosys Foundation runs Springboard digital literacy programs nationally.",
            ),
            (
                "Tata Motors Ltd", "Pimpri", "Vocational Training & Child Education",
                "Bapusaheb Bhadale", "Nodal CSR Officer",
                "b.bhadale@tatamotors.com", "https://www.linkedin.com/company/tata-motors/",
                250.0, 12.0, 0.20, None, "FY25-26", "New Lead",
                "Tata Motors CSR includes skilling and education around its Pimpri-Chinchwad plant.",
            ),
            (
                "Cummins India Ltd", "Kharadi", "Community Education & Skilling",
                "Harmeet Mehra", "CSR Communications Leader",
                "indiacr@cummins.com", "https://www.linkedin.com/company/cummins/",
                180.0, 15.0, 0.25, None, "FY25-26", "New Lead",
                "Cummins India Foundation is active in Pune community education initiatives from Kharadi.",
            ),
            (
                "Persistent Systems Ltd", "Hinjawadi Phase 1", "Digital Literacy & STEM Scholarships",
                "Persistent Foundation Desk", "Lead CSR Executive",
                "core_foundation@persistent.com", "https://www.linkedin.com/company/persistent-systems/",
                90.0, 10.0, 0.20, None, "FY25-26", "New Lead",
                "Persistent Foundation focuses on digital literacy and education technology access.",
            ),
            (
                "Synechron Technologies", "Kharadi", "Primary Education & STEM",
                "Tanveer Saulat", "Corporate Lead",
                "tanveer.saulat@synechron.com", "https://www.linkedin.com/company/synechron/",
                40.0, 8.0, 0.15, None, "FY25-26", "New Lead",
                "Synechron's EON Kharadi campus contact for educational program outreach.",
            ),
            (
                "Thermax Ltd", "Chinchwad", "Community Learning Centers",
                "Thermax Foundation Desk", "Head - Thermax Foundation",
                "csg@thermaxglobal.com", "https://www.linkedin.com/company/thermax-limited/",
                150.0, 12.0, 0.20, None, "FY25-26", "New Lead",
                "Thermax Foundation runs community development and learning-center programs.",
            ),
            (
                "Tech Mahindra Ltd", "Hinjawadi Phase 3", "Tech-Enabled Education",
                "Tech Mahindra Foundation Pune", "Regional CSR Manager",
                "pune@techmahindrafoundation.org", "https://www.linkedin.com/company/tech-mahindra/",
                200.0, 15.0, 0.20, None, "FY25-26", "New Lead",
                "Tech Mahindra Foundation supports tech-for-education initiatives.",
            ),
            (
                "Eaton India", "Kharadi", "Education & Child Welfare",
                "Pratik Shah", "Innovation & CSR Lead",
                "PratikShah@Eaton.com", "https://www.linkedin.com/company/eaton-corporation/",
                60.0, 10.0, 0.20, None, "FY25-26", "New Lead",
                "Eaton India's Kharadi office contact for education and child welfare initiatives.",
            ),
            (
                "Wipro Ltd", "Hinjawadi Phase 2", "Primary Education Quality",
                "Samir Gadgil", "Wipro Cares Pune Head",
                "admin.wiprofoundation@wipro.com", "https://www.linkedin.com/company/wipro/",
                400.0, 18.0, 0.20, None, "FY25-26", "New Lead",
                "Wipro Foundation's Applied Education program targets primary education quality.",
            ),
        ]

        cur.executemany(
            """
            INSERT INTO companies (
                company_name, zone, csr_focus, contact_person, designation,
                email, linkedin_url, csr_budget_lakhs, target_grant_lakhs,
                win_probability, last_contacted_date, financial_year,
                status, last_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seed_rows,
        )


# ----------------------------------------------------------------------------
# CORE CRUD HELPERS
# ----------------------------------------------------------------------------
def get_all_companies() -> List[Dict[str, Any]]:
    """Return every company row as a list of dicts."""
    init_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]


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
    linkedin_url: str,
    status: str = "New Lead",
    notes: str = "",
    csr_budget_lakhs: Optional[float] = None,
    target_grant_lakhs: Optional[float] = None,
    win_probability: float = 0.20,
    financial_year: str = "FY25-26",
) -> int:
    """Insert a new company record. Returns the new row's id."""
    init_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO companies (
                company_name, zone, csr_focus, contact_person, designation,
                email, linkedin_url, csr_budget_lakhs, target_grant_lakhs,
                win_probability, last_contacted_date, financial_year,
                status, last_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name, zone, csr_focus, contact_person, designation,
                email, linkedin_url, csr_budget_lakhs, target_grant_lakhs,
                win_probability, None, financial_year, status, notes,
            ),
        )
        new_id = cur.lastrowid

    log_interaction(new_id, "Lead Created", f"Initial status: {status}")
    return new_id


def update_company_status(company_id: int, new_status: str, notes: str = "") -> None:
    """Update a company's status/notes and log the change."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE companies
            SET status = ?,
                last_notes = ?,
                last_contacted_date = ?
            WHERE id = ?
            """,
            (new_status, notes, date.today().isoformat(), company_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"No company found with id={company_id}")

    log_interaction(
        company_id,
        f"Status changed to '{new_status}'",
        notes,
    )


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
    "designation", "email", "linkedin_url",
]


def bulk_insert_companies(df: pd.DataFrame) -> Dict[str, Any]:
    """Bulk-insert companies from a DataFrame."""
    init_db()

    missing_cols = [c for c in REQUIRED_BULK_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    inserted = 0
    skipped = 0
    errors = []

    with get_connection() as conn:
        cur = conn.cursor()
        for idx, row in df.iterrows():
            try:
                if not str(row.get("company_name", "")).strip():
                    skipped += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO companies (
                        company_name, zone, csr_focus, contact_person,
                        designation, email, linkedin_url, csr_budget_lakhs,
                        target_grant_lakhs, win_probability,
                        last_contacted_date, financial_year, status, last_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("company_name"),
                        row.get("zone"),
                        row.get("csr_focus"),
                        row.get("contact_person"),
                        row.get("designation"),
                        row.get("email"),
                        row.get("linkedin_url"),
                        row.get("csr_budget_lakhs"),
                        row.get("target_grant_lakhs"),
                        row.get("win_probability", 0.20),
                        None,
                        row.get("financial_year", "FY25-26"),
                        row.get("status", "New Lead"),
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
    seed_data(force=True)
    print("Database initialized and seeded with contact entries.")