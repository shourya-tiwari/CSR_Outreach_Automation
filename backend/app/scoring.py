"""Deterministic lead scoring (Phase 3).

Produces a 0-100 score and a High/Medium/Low priority label from data
already on the Company record. This is a fixed, auditable formula -
the same company data always produces the same score, no AI call
involved. See app/ai.py for the LLM-written explanation that
accompanies this score.

Factors (100 points total):
    - CSR focus match with the NGO's own focus areas   (0-40)
    - CSR spending                                      (0-30)
    - Location match with the NGO's own city/state      (0-15)
    - Company size (employee count, as a capacity proxy) (0-15)

Not modeled: the target company's own history of CSR activity - no
structured data source for that is integrated yet (would need e.g.
Form CSR-2 filings or annual reports), so it's left out rather than
faked. See docs/TASKS.md.
"""

from .config import settings
from .models import Company

HIGH_PRIORITY_THRESHOLD = 70
MEDIUM_PRIORITY_THRESHOLD = 40


def _focus_match_score(company_focus: str | None, ngo_focus_areas: list[str]) -> int:
    if not company_focus or not ngo_focus_areas:
        return 0
    company_terms = {t.strip().lower() for t in company_focus.split(",") if t.strip()}
    ngo_terms = {t.strip().lower() for t in ngo_focus_areas}
    if not company_terms:
        return 0
    if company_terms & ngo_terms:
        return 40
    for company_term in company_terms:
        for ngo_term in ngo_terms:
            if company_term in ngo_term or ngo_term in company_term:
                return 25
    return 0


def _spending_score(csr_spending: float | None) -> int:
    if not csr_spending or csr_spending <= 0:
        return 0
    if csr_spending >= 10_000_000:
        return 30
    if csr_spending >= 5_000_000:
        return 22
    if csr_spending >= 1_000_000:
        return 15
    if csr_spending >= 100_000:
        return 8
    return 3


def _location_score(city: str | None, state: str | None) -> int:
    if settings.ngo_city and city and city.strip().lower() == settings.ngo_city.strip().lower():
        return 15
    if settings.ngo_state and state and state.strip().lower() == settings.ngo_state.strip().lower():
        return 8
    return 0


def _size_score(employee_count: int | None) -> int:
    if not employee_count:
        return 0
    if employee_count >= 5000:
        return 15
    if employee_count >= 1000:
        return 10
    if employee_count >= 200:
        return 5
    return 0


def compute_lead_score(company: Company) -> dict:
    factors = {
        "csr_focus_match": _focus_match_score(company.csr_focus, settings.ngo_focus_areas_list),
        "csr_spending": _spending_score(company.csr_spending),
        "location": _location_score(company.city, company.state),
        "company_size": _size_score(company.employee_count),
    }
    score = sum(factors.values())

    if score >= HIGH_PRIORITY_THRESHOLD:
        priority = "High"
    elif score >= MEDIUM_PRIORITY_THRESHOLD:
        priority = "Medium"
    else:
        priority = "Low"

    return {"score": score, "priority": priority, "factors": factors}
