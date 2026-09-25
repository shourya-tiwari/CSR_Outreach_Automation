"""
enrichment.py
--------------
External data-integration module for A Ray of Hope Foundation's CSR
Outreach Portal.

Two responsibilities:
    1. Parse MCA (Ministry of Corporate Affairs) Master Data CSV exports
       to shortlist companies likely subject to Section 135 CSR
       obligations (company name, CIN, registered office/state, and a
       rough CSR-budget estimate).
    2. Provide integration templates for third-party contact-enrichment
       APIs (Hunter.io, Apollo.io) to find verified names/emails for
       CSR-relevant titles ("CSR Manager", "Company Secretary", "Head of
       CSR", etc.) at a given company domain.

API keys are read from environment variables — never hard-code credentials.
Set HUNTER_API_KEY / APOLLO_API_KEY in your shell or .env file.

IMPORTANT — MCA budget estimates are heuristic, not authoritative
--------------------------------------------------------------------
Section 135(5) requires 2% of a company's *average net profit* over the
preceding 3 financial years — a figure the public MCA Master Data export
does not reliably include. The estimator below uses paid-up capital as a
rough sizing proxy purely to help prioritize outreach; always confirm
CSR obligation and budget from the company's actual Annual Report /
Form CSR-2 filing before using a number in a pitch.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enrichment")

REQUEST_TIMEOUT = 10
API_RATE_LIMIT_DELAY_SECONDS = 1.0

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "")
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")

HUNTER_BASE_URL = "https://api.hunter.io/v2"
APOLLO_BASE_URL = "https://api.apollo.io/v1"

# Titles CSR outreach cares about — used to filter Domain Search / People
# Search API results down to the right decision-makers.
TARGET_TITLES = [
    "CSR Manager", "Head of CSR", "CSR Head", "Vice President CSR",
    "Company Secretary", "CSR Lead", "Sustainability Manager",
    "Head of Sustainability", "CSR Officer", "Corporate Affairs Manager",
]


# ============================================================================
# 1. MCA MASTER DATA CSV PARSER
# ============================================================================

# MCA Master Data exports use varying header casings/spacing across
# releases; normalize by matching on lowercased, stripped keys.
_MCA_COLUMN_ALIASES = {
    "company_name": ["company name", "company_name", "companyname", "name of company"],
    "cin": ["cin", "corporate identification number"],
    "registered_office": [
        "registered office address", "registered_office_address",
        "regd office address", "address",
    ],
    "state": ["state", "roc_state", "registered state"],
    "roc_code": ["roc code", "roc_code", "roc"],
    "paidup_capital": [
        "paid up capital", "paidup_capital", "authorized capital",
        "paid-up capital(rs)", "paid up capital(rs.)",
    ],
    "company_status": ["company status", "status", "company_status"],
    "date_of_registration": ["date of registration", "date_of_registration"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renames whatever columns are present in an MCA CSV export to our
    canonical schema, based on _MCA_COLUMN_ALIASES. Unmatched columns are left as-is."""
    lower_map = {c.lower().strip(): c for c in df.columns}
    rename_map = {}

    for canonical, aliases in _MCA_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                rename_map[lower_map[alias]] = canonical
                break

    return df.rename(columns=rename_map)


def parse_mca_master_data(csv_path: str, min_paidup_capital_lakhs: float = 100.0) -> pd.DataFrame:
    """
    Parses an MCA Master Data CSV export into a normalized DataFrame with
    columns: company_name, cin, registered_office, state, roc_code,
    paidup_capital_lakhs, company_status, csr_budget_estimate_lakhs.

    Args:
        csv_path: path to the MCA Master Data CSV file.
        min_paidup_capital_lakhs: filters out very small entities unlikely
            to meet Section 135 thresholds (default ₹1 Crore = 100 Lakhs).

    Returns:
        A cleaned DataFrame sorted by estimated CSR budget, descending.
    """
    raw = pd.read_csv(csv_path, low_memory=False)
    df = _normalize_columns(raw)

    required = ["company_name", "cin"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"MCA CSV is missing required column(s) after normalization: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Coerce paid-up capital to numeric Lakhs (MCA exports it in Rupees)
    if "paidup_capital" in df.columns:
        df["paidup_capital"] = pd.to_numeric(
            df["paidup_capital"].astype(str).str.replace(r"[^\d.]", "", regex=True),
            errors="coerce",
        )
        df["paidup_capital_lakhs"] = (df["paidup_capital"] / 100_000).round(2)
    else:
        df["paidup_capital_lakhs"] = pd.NA

    # Keep only active companies if status column is present
    if "company_status" in df.columns:
        df = df[df["company_status"].astype(str).str.lower().str.contains("active", na=False)]

    if "paidup_capital_lakhs" in df.columns:
        df = df[df["paidup_capital_lakhs"].fillna(0) >= min_paidup_capital_lakhs]

    df["csr_budget_estimate_lakhs"] = df["paidup_capital_lakhs"].apply(_estimate_csr_budget)

    keep_cols = [
        c for c in [
            "company_name", "cin", "registered_office", "state", "roc_code",
            "paidup_capital_lakhs", "company_status", "csr_budget_estimate_lakhs",
        ] if c in df.columns
    ]
    result = df[keep_cols].drop_duplicates(subset="cin").reset_index(drop=True)
    return result.sort_values("csr_budget_estimate_lakhs", ascending=False).reset_index(drop=True)


def _estimate_csr_budget(paidup_capital_lakhs: Optional[float]) -> Optional[float]:
    """
    VERY rough CSR-budget sizing heuristic based on paid-up capital, used
    only to prioritize which companies to research/contact first.
    Not a substitute for actual net-profit-based Section 135(5) figures.
    """
    if pd.isna(paidup_capital_lakhs) or paidup_capital_lakhs <= 0:
        return None
    # Illustrative multiplier only — tune against known real CSR spends
    # in your sector before relying on this for prioritization.
    return round(paidup_capital_lakhs * 0.02, 2)


def filter_by_state(df: pd.DataFrame, state: str = "Maharashtra") -> pd.DataFrame:
    """Convenience filter for companies registered in a given state."""
    if "state" not in df.columns:
        return df
    return df[df["state"].astype(str).str.lower() == state.lower()].reset_index(drop=True)


# ============================================================================
# 2. THIRD-PARTY CONTACT ENRICHMENT (Hunter.io / Apollo.io)
# ============================================================================

@dataclass
class EnrichedContact:
    company_domain: str
    full_name: str
    designation: str
    email: str
    email_confidence: Optional[int]
    linkedin_url: str
    source: str


def _require_api_key(key: str, service: str) -> None:
    if not key:
        raise EnvironmentError(
            f"{service} API key not set. Export it as an environment variable "
            f"before calling this function (e.g. {service.upper()}_API_KEY)."
        )


# --- Hunter.io ---------------------------------------------------------------
def hunter_domain_search(domain: str, titles: Optional[List[str]] = None) -> List[EnrichedContact]:
    """
    Uses Hunter.io's Domain Search API to list known email addresses at a
    company domain, filtered down to CSR-relevant titles.

    Docs: https://hunter.io/api-documentation/v2#domain-search
    """
    _require_api_key(HUNTER_API_KEY, "hunter")
    titles = titles or TARGET_TITLES

    params = {"domain": domain, "api_key": HUNTER_API_KEY, "limit": 25}

    try:
        resp = requests.get(f"{HUNTER_BASE_URL}/domain-search", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Hunter.io domain search failed for {domain}: {e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_DELAY_SECONDS)

    payload = resp.json().get("data", {})
    emails = payload.get("emails", [])

    results = []
    for entry in emails:
        position = (entry.get("position") or "").strip()
        if not position or not any(t.lower() in position.lower() for t in titles):
            continue
        results.append(
            EnrichedContact(
                company_domain=domain,
                full_name=f"{entry.get('first_name', '')} {entry.get('last_name', '')}".strip(),
                designation=position,
                email=entry.get("value", ""),
                email_confidence=entry.get("confidence"),
                linkedin_url=entry.get("linkedin", "") or "",
                source="hunter.io",
            )
        )
    return results


def hunter_find_email(domain: str, first_name: str, last_name: str) -> Optional[EnrichedContact]:
    """
    Uses Hunter.io's Email Finder API to guess/verify a specific person's
    work email once you already know their name and company domain
    (e.g. a name sourced from LinkedIn or the company's website).

    Docs: https://hunter.io/api-documentation/v2#email-finder
    """
    _require_api_key(HUNTER_API_KEY, "hunter")

    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": HUNTER_API_KEY,
    }

    try:
        resp = requests.get(f"{HUNTER_BASE_URL}/email-finder", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Hunter.io email finder failed for {first_name} {last_name} @ {domain}: {e}")
        return None
    finally:
        time.sleep(API_RATE_LIMIT_DELAY_SECONDS)

    data = resp.json().get("data", {})
    if not data.get("email"):
        return None

    return EnrichedContact(
        company_domain=domain,
        full_name=f"{first_name} {last_name}",
        designation=data.get("position", "") or "",
        email=data["email"],
        email_confidence=data.get("score"),
        linkedin_url="",
        source="hunter.io",
    )


# --- Apollo.io ----------------------------------------------------------------
def apollo_people_search(
    domain: str, titles: Optional[List[str]] = None, per_page: int = 10
) -> List[EnrichedContact]:
    """
    Uses Apollo.io's People Search API to find people matching CSR-relevant
    titles at a given company domain.

    Docs: https://docs.apollo.io/reference/people-search
    """
    _require_api_key(APOLLO_API_KEY, "apollo")
    titles = titles or TARGET_TITLES

    headers = {"Content-Type": "application/json", "X-Api-Key": APOLLO_API_KEY}
    body = {
        "q_organization_domains": domain,
        "person_titles": titles,
        "page": 1,
        "per_page": per_page,
    }

    try:
        resp = requests.post(
            f"{APOLLO_BASE_URL}/mixed_people/search",
            json=body, headers=headers, timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Apollo.io people search failed for {domain}: {e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_DELAY_SECONDS)

    people = resp.json().get("people", [])

    results = []
    for person in people:
        results.append(
            EnrichedContact(
                company_domain=domain,
                full_name=person.get("name", ""),
                designation=person.get("title", ""),
                email=person.get("email", "") or "",
                email_confidence=None,
                linkedin_url=person.get("linkedin_url", "") or "",
                source="apollo.io",
            )
        )
    return results


# ============================================================================
# 3. ORCHESTRATION HELPERS
# ============================================================================

def enrich_domain(domain: str, prefer: str = "hunter") -> List[EnrichedContact]:
    """
    Tries the preferred enrichment provider first, falling back to the
    other if no results (or if the preferred key isn't configured).

    Args:
        domain: company website domain, e.g. "persistent.com"
        prefer: "hunter" or "apollo"
    """
    providers = {
        "hunter": lambda: hunter_domain_search(domain),
        "apollo": lambda: apollo_people_search(domain),
    }
    order = [prefer] + [p for p in providers if p != prefer]

    for provider in order:
        try:
            results = providers[provider]()
            if results:
                return results
        except EnvironmentError as e:
            logger.info(f"{provider} skipped: {e}")
            continue

    return []


def enrichment_results_to_db_kwargs(contact: EnrichedContact) -> Dict[str, str]:
    """
    Maps an EnrichedContact onto the keyword arguments expected by
    database.add_company() / database.update_company(), so results can be
    written straight into the pipeline.
    """
    return {
        "contact_person": contact.full_name,
        "designation": contact.designation,
        "email": contact.email,
        "linkedin_url": contact.linkedin_url,
        "last_notes": f"Enriched via {contact.source} (confidence: {contact.email_confidence})",
    }


if __name__ == "__main__":
    # Example: parse a local MCA export and preview the top prospects.
    # Replace with a real MCA Master Data CSV path before running.
    import sys

    if len(sys.argv) > 1:
        mca_df = parse_mca_master_data(sys.argv[1])
        pune_prospects = filter_by_state(mca_df, "Maharashtra")
        print(pune_prospects.head(15).to_string(index=False))
    else:
        print("Usage: python enrichment.py <path_to_mca_master_data.csv>")