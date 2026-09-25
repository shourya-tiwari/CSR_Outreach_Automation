"""
config.py
---------
Central configuration for A Ray of Hope Foundation's CSR Outreach Portal.
Holds static reference data (zones, focus domains), validation regex
patterns, and environment-driven API/service configuration.

No secrets are hard-coded here — all keys/URLs are read from environment
variables with safe local-dev fallbacks.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List

# ----------------------------------------------------------------------------
# APP METADATA
# ----------------------------------------------------------------------------
APP_NAME = "A Ray of Hope Foundation - CSR Corporate Outreach Portal"
APP_ICON = "🤝"
ORG_NAME = "A Ray of Hope Foundation"
ORG_CITY = "Pune"

# ----------------------------------------------------------------------------
# TARGET ZONES (Pune industrial / IT belts)
# ----------------------------------------------------------------------------
PUNE_ZONES: List[str] = [
    "Hinjawadi Phase 1",
    "Hinjawadi Phase 2",
    "Hinjawadi Phase 3",
    "Kharadi (EON IT Park)",
    "Bhosari MIDC",
    "Chakan Industrial Area",
    "Pimpri-Chinchwad",
    "Magarpatta",
    "Viman Nagar",
    "Baner",
]

ZONE_FILTER_OPTIONS: List[str] = ["All"] + PUNE_ZONES

# ----------------------------------------------------------------------------
# CSR FOCUS DOMAINS (aligned to Schedule VII, Companies Act 2013)
# ----------------------------------------------------------------------------
CSR_FOCUS_AREAS: List[str] = [
    "Primary Education & Literacy",
    "Digital Literacy / EdTech",
    "Vocational Training & Skilling",
    "STEM Education",
    "Child Welfare & Nutrition",
    "Community Learning Centers",
    "Girl Child Education",
    "Special Needs / Inclusive Education",
    "Teacher Training & Capacity Building",
    "School Infrastructure",
]

CSR_FOCUS_FILTER_OPTIONS: List[str] = ["All"] + CSR_FOCUS_AREAS

# ----------------------------------------------------------------------------
# LEAD STATUS PIPELINE
# ----------------------------------------------------------------------------
LEAD_STATUSES: List[str] = [
    "New Lead",
    "Contacted",
    "In Discussion",
    "Proposal Sent",
    "Pitch Sent",
    "Due Diligence",
    "Funded",
    "Not Interested",
    "On Hold",
]

# Statuses considered "in active pipeline" for weighted forecasting
ACTIVE_PIPELINE_STATUSES: List[str] = [
    "Contacted",
    "In Discussion",
    "Proposal Sent",
    "Pitch Sent",
    "Due Diligence",
]

CLOSED_WON_STATUSES: List[str] = ["Funded"]
CLOSED_LOST_STATUSES: List[str] = ["Not Interested"]

# Default win-probability weighting per status (used by compliance_engine)
STATUS_WIN_PROBABILITY = {
    "New Lead": 0.05,
    "Contacted": 0.10,
    "In Discussion": 0.25,
    "Proposal Sent": 0.40,
    "Pitch Sent": 0.45,
    "Due Diligence": 0.65,
    "Funded": 1.00,
    "Not Interested": 0.00,
    "On Hold": 0.05,
}

# ----------------------------------------------------------------------------
# FINANCIAL YEAR CONFIG (Indian FY: April 1 - March 31)
# ----------------------------------------------------------------------------
FY_START_MONTH = 4          # April
FY_END_MONTH = 3            # March
FY_Q4_START_MONTH = 1       # January
CSR_SPEND_DEADLINE_MONTH = 3
CSR_SPEND_DEADLINE_DAY = 31

# Days-remaining thresholds for urgency banding (used in compliance_engine)
Q4_URGENCY_THRESHOLDS = {
    "critical": 30,   # <=30 days to FY close
    "high": 60,       # <=60 days
    "moderate": 90,   # <=90 days
}

# ----------------------------------------------------------------------------
# VALIDATION REGEX PATTERNS
# ----------------------------------------------------------------------------
REGEX_PATTERNS = {
    # Standard RFC-5322-lite email pattern, good enough for form validation
    "email": re.compile(
        r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    ),
    # Indian mobile numbers (optional +91 / 0 prefix) and generic 10-digit
    "phone": re.compile(
        r"^(?:\+91[\-\s]?|0)?[6-9]\d{9}$"
    ),
    # LinkedIn personal or company profile URLs
    "linkedin": re.compile(
        r"^https?:\/\/(www\.)?linkedin\.com\/(in|company)\/[A-Za-z0-9\-_%]+\/?$"
    ),
    # Indian currency amounts expressed in Lakhs/Crores, e.g. "15.5 Lakhs", "2 Cr", "₹15,00,000"
    "money_lakhs_crores": re.compile(
        r"^₹?\s?[\d,]+(\.\d+)?\s?(Lakhs?|L|Crores?|Cr)?$",
        re.IGNORECASE,
    ),
    # Plain numeric currency with optional commas and decimals, e.g. 1,50,000.00
    "money_numeric": re.compile(
        r"^₹?\s?\d{1,3}(,\d{2,3})*(\.\d{1,2})?$"
    ),
    # Financial year label, e.g. FY25-26
    "financial_year": re.compile(
        r"^FY\d{2}-\d{2}$"
    ),
}


def is_valid_email(value: str) -> bool:
    return bool(value) and bool(REGEX_PATTERNS["email"].match(value.strip()))


def is_valid_phone(value: str) -> bool:
    return bool(value) and bool(REGEX_PATTERNS["phone"].match(value.strip()))


def is_valid_linkedin(value: str) -> bool:
    return bool(value) and bool(REGEX_PATTERNS["linkedin"].match(value.strip()))


def is_valid_money(value: str) -> bool:
    if not value:
        return False
    v = value.strip()
    return bool(
        REGEX_PATTERNS["money_lakhs_crores"].match(v)
        or REGEX_PATTERNS["money_numeric"].match(v)
    )


# ----------------------------------------------------------------------------
# API KEYS / SERVICE CONFIGURATION
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class APIConfig:
    """
    Reads service configuration from environment variables.
    No secrets are stored in source — set these in your shell,
    a .env file (loaded via python-dotenv), or your deployment
    platform's secrets manager before running the app.
    """
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    anthropic_api_url: str = field(
        default_factory=lambda: os.environ.get(
            "ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"
        )
    )
    anthropic_model: str = field(
        default_factory=lambda: os.environ.get(
            "ANTHROPIC_MODEL", "claude-sonnet-4-6"
        )
    )

    email_smtp_host: str = field(
        default_factory=lambda: os.environ.get("SMTP_HOST", "smtp.gmail.com")
    )
    email_smtp_port: int = field(
        default_factory=lambda: int(os.environ.get("SMTP_PORT", "587"))
    )
    email_smtp_user: str = field(
        default_factory=lambda: os.environ.get("SMTP_USER", "")
    )
    email_smtp_password: str = field(
        default_factory=lambda: os.environ.get("SMTP_PASSWORD", "")
    )

    linkedin_api_key: str = field(
        default_factory=lambda: os.environ.get("LINKEDIN_API_KEY", "")
    )

    def is_ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    def is_email_enabled(self) -> bool:
        return bool(self.email_smtp_user and self.email_smtp_password)


API_CONFIG = APIConfig()

# ----------------------------------------------------------------------------
# DATABASE CONFIG
# ----------------------------------------------------------------------------
DB_PATH = os.environ.get("CSR_DB_PATH", "data/csr_tracker.db")

# ----------------------------------------------------------------------------
# COMPLIANCE / TAX REFERENCE DATA
# ----------------------------------------------------------------------------
# Whether the NGO holds each certification — flip to True once verified
# and store certificate numbers/expiry via environment or a secrets file,
# not hard-coded here.
NGO_CERTIFICATIONS = {
    "csr1_registered": True,
    "csr1_registration_no": os.environ.get("CSR1_REG_NO", "CSR00000000"),
    "80g_certified": True,
    "80g_certificate_no": os.environ.get("REG_80G_NO", ""),
    "12a_certified": True,
    "12a_certificate_no": os.environ.get("REG_12A_NO", ""),
    "fcra_registered": False,
}