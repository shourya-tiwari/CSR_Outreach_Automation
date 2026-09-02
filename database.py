"""
database.py
Sets up and manages the SQLite database (csr_portal.db) for the
CSR Outreach & Lead Tracker Dashboard - A Ray of Hope Foundation.
"""

import sqlite3
import pandas as pd

DB_NAME = "csr_portal.db"

STATUS_OPTIONS = [
    "New Lead", "Contacted", "In Discussion", "Pitch Sent", "Funded", "Declined"
]


def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Creates the companies table if it doesn't already exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                zone TEXT,
                csr_focus TEXT,
                contact_person TEXT,
                designation TEXT,
                email TEXT,
                linkedin_url TEXT,
                status TEXT DEFAULT 'New Lead',
                last_notes TEXT
            )
        """)
        conn.commit()


def seed_data():
    """Pre-populates the companies table with realistic Pune corporate leads,
    only if the table is currently empty."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        if count > 0:
            print("Database already contains data. Skipping seed.")
            return

        companies = [
            ("Infosys", "Hinjawadi", "Education & Child Welfare", "Anjali Deshpande", "Head of CSR",
             "anjali.deshpande@infosys.com", "linkedin.com/in/anjalideshpande", "New Lead",
             "Interested in digital classrooms initiative."),
            ("Tata Motors", "Pimpri", "Skill Development", "Rohan Kulkarni", "VP Operations",
             "rohan.kulkarni@tatamotors.com", "linkedin.com/in/rohankulkarni", "Contacted",
             "Prior partnership with ITI programs; follow up for renewal."),
            ("Wipro", "Hinjawadi", "Digital Literacy", "Sneha Patil", "HR Director",
             "sneha.patil@wipro.com", "linkedin.com/in/snehapatil", "New Lead",
             "Reached out via LinkedIn, awaiting response."),
            ("Tech Mahindra", "Hinjawadi", "Education & Child Welfare", "Aditya Rane", "Head of CSR",
             "aditya.rane@techmahindra.com", "linkedin.com/in/adityarane", "In Discussion",
             "Positive first call; scheduling site visit to school."),
            ("Bharat Forge", "Chakan", "Skill Development", "Meera Joshi", "CSR Manager",
             "meera.joshi@bharatforge.com", "linkedin.com/in/meerajoshi", "New Lead",
             "Focus on vocational training for youth in Chakan belt."),
            ("Synechron", "Kharadi", "Education & Child Welfare", "Kunal Shah", "VP HR",
             "kunal.shah@synechron.com", "linkedin.com/in/kunalshah", "Pitch Sent",
             "Proposal sent for after-school learning centers."),
            ("Cummins India", "Kharadi", "Education & Child Welfare", "Priya Nair", "Head of CSR",
             "priya.nair@cummins.com", "linkedin.com/in/priyanair", "Funded",
             "Approved grant for 2 learning centers, FY25-26."),
            ("Persistent Systems", "Hinjawadi", "Digital Literacy", "Varun Iyer", "HR Director",
             "varun.iyer@persistent.com", "linkedin.com/in/varuniyer", "New Lead",
             "Known for tech-for-good initiatives; good fit."),
            ("Thermax", "Chinchwad", "Skill Development", "Neha Gokhale", "CSR Manager",
             "neha.gokhale@thermax.com", "linkedin.com/in/nehagokhale", "Contacted",
             "Introductory email sent, no response yet."),
            ("KPIT Technologies", "Hinjawadi", "Education & Child Welfare", "Siddharth Bhosale",
             "Head of CSR", "siddharth.bhosale@kpit.com", "linkedin.com/in/siddharthbhosale",
             "New Lead", "Target for Q3 outreach."),
            ("Sandvik", "Pimpri", "Skill Development", "Rutuja More", "VP Operations",
             "rutuja.more@sandvik.com", "linkedin.com/in/rutujamore", "In Discussion",
             "Interested in sponsoring skill labs at partner schools."),
            ("Alfa Laval", "Bhosari MIDC", "Education & Child Welfare", "Omkar Deshmukh",
             "HR Director", "omkar.deshmukh@alfalaval.com", "linkedin.com/in/omkardeshmukh",
             "New Lead", "Manufacturing hub; strong local community focus."),
            ("Bajaj Auto", "Chakan", "Healthcare", "Pooja Kale", "Head of CSR",
             "pooja.kale@bajajauto.com", "linkedin.com/in/poojakale", "Declined",
             "Budget allocated to healthcare camps this cycle."),
            ("Emerson", "Kharadi", "Education & Child Welfare", "Abhishek Pawar", "CSR Manager",
             "abhishek.pawar@emerson.com", "linkedin.com/in/abhishekpawar", "New Lead",
             "New entrant to Kharadi campus; worth an introductory pitch."),
        ]

        conn.executemany("""
            INSERT INTO companies
            (company_name, zone, csr_focus, contact_person, designation,
             email, linkedin_url, status, last_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, companies)
        conn.commit()
        print(f"Seeded {len(companies)} companies.")


def get_all_companies():
    """Returns all companies as a pandas DataFrame."""
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM companies ORDER BY id", conn)


def add_company(company_name, zone, csr_focus, contact_person, designation,
                 email, linkedin_url, status="New Lead", last_notes=""):
    """Inserts a new company lead into the database."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO companies
            (company_name, zone, csr_focus, contact_person, designation,
             email, linkedin_url, status, last_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_name, zone, csr_focus, contact_person, designation,
              email, linkedin_url, status, last_notes))
        conn.commit()


def update_company_status(company_id, new_status, notes=""):
    """Updates status and notes for a specific company ID."""
    if new_status not in STATUS_OPTIONS:
        raise ValueError(f"Invalid status. Must be one of {STATUS_OPTIONS}")
    with get_connection() as conn:
        conn.execute("""
            UPDATE companies
            SET status = ?, last_notes = ?
            WHERE id = ?
        """, (new_status, notes, company_id))
        conn.commit()


if __name__ == "__main__":
    init_db()
    seed_data()
    print("Database setup complete:", DB_NAME)