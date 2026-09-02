"""
compliance_engine.py
---------------------
Business logic layer for A Ray of Hope Foundation's CSR Outreach Portal.

Responsibilities:
    - Render CSR-1 / 80G / 12A tax-exemption compliance badges (for
      display in Streamlit or any other UI layer).
    - Calculate financial-year (April-March) urgency ("Q4 Alert") based
      on days remaining until the March 31 CSR spend deadline.
    - Compute weighted pipeline value from lead status / win probability.
    - Calculate impact metrics (children reached, cost-per-beneficiary,
      etc.) from funded/target grant amounts.

This module contains pure business logic only — no DB access, no
Streamlit imports — so it can be unit-tested and reused across UI layers.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Union

from config import (
    NGO_CERTIFICATIONS,
    Q4_URGENCY_THRESHOLDS,
    STATUS_WIN_PROBABILITY,
    ACTIVE_PIPELINE_STATUSES,
    CLOSED_WON_STATUSES,
    FY_START_MONTH,
)

Number = Union[int, float]


# ----------------------------------------------------------------------------
# COMPLIANCE / TAX-EXEMPTION BADGES
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class ComplianceBadge:
    label: str
    active: bool
    icon: str
    description: str
    reference_no: str = ""

    def render_markdown(self) -> str:
        """Return a small Markdown chip suitable for st.markdown(unsafe_allow_html=False contexts)."""
        status_icon = "✅" if self.active else "⚠️"
        ref = f" (`{self.reference_no}`)" if self.active and self.reference_no else ""
        return f"{status_icon} **{self.label}**{ref} — {self.description}"


def get_compliance_badges() -> List[ComplianceBadge]:
    """
    Build the set of compliance/tax-exemption badges for the NGO based on
    config.NGO_CERTIFICATIONS. Corporates use these to validate CSR-1
    eligibility and 80G tax deduction eligibility before funding.
    """
    badges = [
        ComplianceBadge(
            label="CSR-1 Registered",
            active=bool(NGO_CERTIFICATIONS.get("csr1_registered")),
            icon="📋",
            description="Eligible to receive CSR funds under Section 135, Companies Act 2013",
            reference_no=NGO_CERTIFICATIONS.get("csr1_registration_no", ""),
        ),
        ComplianceBadge(
            label="80G Certified",
            active=bool(NGO_CERTIFICATIONS.get("80g_certified")),
            icon="💰",
            description="Donors eligible for tax deduction under Section 80G of the Income Tax Act",
            reference_no=NGO_CERTIFICATIONS.get("80g_certificate_no", ""),
        ),
        ComplianceBadge(
            label="12A Certified",
            active=bool(NGO_CERTIFICATIONS.get("12a_certified")),
            icon="🏛️",
            description="NGO income exempt from tax under Section 12A of the Income Tax Act",
            reference_no=NGO_CERTIFICATIONS.get("12a_certificate_no", ""),
        ),
        ComplianceBadge(
            label="FCRA Registered",
            active=bool(NGO_CERTIFICATIONS.get("fcra_registered")),
            icon="🌍",
            description="Eligible to receive foreign contributions under FCRA, 2010",
            reference_no="",
        ),
    ]
    return badges


def compliance_summary_line() -> str:
    """One-line summary of active compliance badges, e.g. 'CSR-1 · 80G · 12A'."""
    active_labels = [b.label.split(" ")[0] for b in get_compliance_badges() if b.active]
    return " · ".join(active_labels) if active_labels else "No active certifications on file"


# ----------------------------------------------------------------------------
# FINANCIAL YEAR / Q4 URGENCY CALCULATION
# ----------------------------------------------------------------------------
def get_current_financial_year(as_of: Optional[date] = None) -> str:
    """
    Return the Indian financial year label (e.g. 'FY25-26') for a given date.
    FY runs April 1 - March 31.
    """
    as_of = as_of or date.today()
    if as_of.month >= FY_START_MONTH:
        start_yy = as_of.year % 100
        end_yy = (as_of.year + 1) % 100
    else:
        start_yy = (as_of.year - 1) % 100
        end_yy = as_of.year % 100
    return f"FY{start_yy:02d}-{end_yy:02d}"


def get_fy_end_date(as_of: Optional[date] = None) -> date:
    """Return the March 31 date that closes the current financial year."""
    as_of = as_of or date.today()
    if as_of.month >= FY_START_MONTH:
        return date(as_of.year + 1, 3, 31)
    return date(as_of.year, 3, 31)


@dataclass(frozen=True)
class Q4UrgencyStatus:
    days_remaining: int
    level: str          # "critical" | "high" | "moderate" | "normal"
    label: str
    icon: str
    fy_label: str
    fy_end_date: date

    def render_markdown(self) -> str:
        return f"{self.icon} **{self.label}** — {self.days_remaining} days left in {self.fy_label} (closes {self.fy_end_date.strftime('%d %b %Y')})"


def calculate_q4_urgency(as_of: Optional[date] = None) -> Q4UrgencyStatus:
    """
    Calculate how urgently outreach should be pushed based on days
    remaining until the March 31 CSR spend deadline. Corporates rush to
    finalize CSR spend in Q4 (Jan-Mar), so this drives an "urgency badge"
    in the UI to prioritize outreach.
    """
    as_of = as_of or date.today()
    fy_end = get_fy_end_date(as_of)
    days_remaining = (fy_end - as_of).days

    if days_remaining <= Q4_URGENCY_THRESHOLDS["critical"]:
        level, label, icon = "critical", "Critical - FY Closing Imminently", "🔴"
    elif days_remaining <= Q4_URGENCY_THRESHOLDS["high"]:
        level, label, icon = "high", "High Urgency - Q4 Spend Window", "🟠"
    elif days_remaining <= Q4_URGENCY_THRESHOLDS["moderate"]:
        level, label, icon = "moderate", "Moderate - Approaching Q4", "🟡"
    else:
        level, label, icon = "normal", "Normal - Plenty of Runway", "🟢"

    return Q4UrgencyStatus(
        days_remaining=max(days_remaining, 0),
        level=level,
        label=label,
        icon=icon,
        fy_label=get_current_financial_year(as_of),
        fy_end_date=fy_end,
    )


# ----------------------------------------------------------------------------
# WEIGHTED PIPELINE CALCULATIONS
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class PipelineSummary:
    total_leads: int
    active_leads: int
    total_target_lakhs: float
    weighted_pipeline_lakhs: float
    funded_lakhs: float
    conversion_rate_pct: float


def calculate_weighted_value(
    target_grant_lakhs: Optional[Number],
    status: str,
    win_probability: Optional[Number] = None,
) -> float:
    """
    Weighted expected value of a single lead = target grant amount x
    probability of closing, based on either an explicit win_probability
    or the default probability mapped to its current status.
    """
    if not target_grant_lakhs:
        return 0.0

    prob = win_probability
    if prob is None or prob == "":
        prob = STATUS_WIN_PROBABILITY.get(status, 0.20)

    try:
        return round(float(target_grant_lakhs) * float(prob), 2)
    except (TypeError, ValueError):
        return 0.0


def calculate_pipeline_summary(companies: Sequence[Dict]) -> PipelineSummary:
    """
    Aggregate a weighted pipeline summary across a list of company dict
    records (as returned by database.get_all_companies()).

    Expected keys per record: 'status', 'target_grant_lakhs',
    'win_probability', 'csr_budget_lakhs'.
    """
    total_leads = len(companies)
    active_leads = 0
    total_target = 0.0
    weighted_total = 0.0
    funded_total = 0.0

    for c in companies:
        status = c.get("status", "New Lead")
        target = c.get("target_grant_lakhs") or 0.0
        prob = c.get("win_probability")

        total_target += float(target or 0.0)

        if status in ACTIVE_PIPELINE_STATUSES:
            active_leads += 1
            weighted_total += calculate_weighted_value(target, status, prob)

        if status in CLOSED_WON_STATUSES:
            funded_total += float(target or 0.0)

    conversion_rate = (
        round((funded_total / total_target) * 100, 1) if total_target > 0 else 0.0
    )

    return PipelineSummary(
        total_leads=total_leads,
        active_leads=active_leads,
        total_target_lakhs=round(total_target, 2),
        weighted_pipeline_lakhs=round(weighted_total, 2),
        funded_lakhs=round(funded_total, 2),
        conversion_rate_pct=conversion_rate,
    )


def rank_leads_by_weighted_value(companies: Sequence[Dict], top_n: int = 10) -> List[Dict]:
    """
    Return the top-N active leads ranked by weighted expected value
    (target_grant_lakhs x win_probability), highest first. Useful for a
    "priority outreach" view.
    """
    scored = []
    for c in companies:
        weighted = calculate_weighted_value(
            c.get("target_grant_lakhs"), c.get("status", "New Lead"), c.get("win_probability")
        )
        scored.append({**c, "weighted_value_lakhs": weighted})

    scored.sort(key=lambda x: x["weighted_value_lakhs"], reverse=True)
    return scored[:top_n]


# ----------------------------------------------------------------------------
# IMPACT METRIC CALCULATORS
# ----------------------------------------------------------------------------
# Reference unit-economics for the NGO's education programs. These are
# operational assumptions the NGO should tune to its own program costs.
DEFAULT_COST_PER_CHILD_PER_YEAR_INR = 8000  # ₹8,000/child/year, illustrative baseline
LAKH_TO_INR = 100_000


@dataclass(frozen=True)
class ImpactEstimate:
    grant_amount_lakhs: float
    grant_amount_inr: float
    estimated_children_reached: int
    cost_per_child_inr: float


def estimate_impact(
    grant_amount_lakhs: Number,
    cost_per_child_inr: Number = DEFAULT_COST_PER_CHILD_PER_YEAR_INR,
) -> ImpactEstimate:
    """
    Translate a funded grant amount (in Lakhs INR) into an estimated
    number of children reached per year, given a per-child annual cost.
    """
    grant_amount_lakhs = float(grant_amount_lakhs or 0.0)
    cost_per_child_inr = float(cost_per_child_inr or DEFAULT_COST_PER_CHILD_PER_YEAR_INR)

    grant_amount_inr = grant_amount_lakhs * LAKH_TO_INR
    children_reached = int(grant_amount_inr // cost_per_child_inr) if cost_per_child_inr > 0 else 0

    return ImpactEstimate(
        grant_amount_lakhs=round(grant_amount_lakhs, 2),
        grant_amount_inr=round(grant_amount_inr, 2),
        estimated_children_reached=children_reached,
        cost_per_child_inr=cost_per_child_inr,
    )


def calculate_total_impact(companies: Sequence[Dict]) -> Dict[str, Number]:
    """
    Aggregate estimated impact across all *funded* leads
    (status in CLOSED_WON_STATUSES).
    """
    total_funded_lakhs = sum(
        float(c.get("target_grant_lakhs") or 0.0)
        for c in companies
        if c.get("status") in CLOSED_WON_STATUSES
    )
    impact = estimate_impact(total_funded_lakhs)

    return {
        "total_funded_lakhs": impact.grant_amount_lakhs,
        "total_funded_inr": impact.grant_amount_inr,
        "estimated_children_reached": impact.estimated_children_reached,
        "cost_per_child_inr": impact.cost_per_child_inr,
    }


def cost_per_beneficiary(total_spend_lakhs: Number, beneficiaries_reached: int) -> float:
    """Simple cost-efficiency metric: total spend (INR) / number of beneficiaries."""
    if not beneficiaries_reached:
        return 0.0
    total_spend_inr = float(total_spend_lakhs or 0.0) * LAKH_TO_INR
    return round(total_spend_inr / beneficiaries_reached, 2)