"""
modules/compliance_engine.py

Compliance & impact-economics engine for the CSR Outreach & Lead Tracker
Dashboard - A Ray of Hope Foundation (Pune).

Covers:
  - Section 135(5) Companies Act, 2013 "unspent CSR" Q4 urgency messaging
  - Statutory credential display (CSR-1 / 80G / 12A)
  - Per-lakh impact modelling for pitch decks
  - Probability-weighted pipeline forecasting

IMPORTANT COMPLIANCE NOTE
--------------------------
The constants in NGO_CREDENTIALS below are PLACEHOLDERS. Before this
dashboard is shown to any prospective donor, verify each number against:
  - MCA CSR-1 filing acknowledgement
  - Income Tax Dept 80G registration order (Form 10AC)
  - 12A registration order / NITI Aayog Darpan portal
Do not present unverified registration numbers as "Verified" in a live pitch.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration — replace with NGO-verified values before production use
# ---------------------------------------------------------------------------

NGO_CREDENTIALS = {
    "csr1_reg_no": "CSR00034821",
    "80g_cert_id": "IT/80G/2021-22/A-492",
    "12a_reg_id": "MH/2018/0192842",
    "darpan_id": "MH/2018/0192842",  # confirm this is distinct from 12A if applicable
    "verified_as_of": None,  # e.g. "2026-04-01" — set once NGO confirms these
}

# Section 135(5) proviso: unspent CSR amount (not tied to an ongoing project)
# must be transferred to a Schedule VII fund (e.g. PM CARES) within 6 months
# of the financial year's end (i.e. by ~30 Sep) if not spent by 31 Mar.
FY_END_MONTH = 3
FY_END_DAY = 31
Q4_MONTHS = {1, 2, 3}

# Impact model constants (per ₹1 Lakh)
CHILDREN_PER_LAKH = 25
KITS_PER_LAKH = 1
CENTERS_PER_LAKH = 0.1  # i.e. 1 learning center fully equipped per ₹10L


# ---------------------------------------------------------------------------
# 1. Q4 unspent-funds urgency alert
# ---------------------------------------------------------------------------

@dataclass
class Q4AlertResult:
    is_q4: bool
    days_to_fy_end: Optional[int]
    pitch_prefix: str
    pitch_urgency_line: str


def _get_fy_end_date(today: _dt.date) -> _dt.date:
    """Returns the current financial year's closing date (31 Mar)."""
    year = today.year if today.month <= FY_END_MONTH else today.year + 1
    return _dt.date(year, FY_END_MONTH, FY_END_DAY)


def render_march31_alert(today: Optional[_dt.date] = None) -> Q4AlertResult:
    """
    Checks whether the system is currently in CSR Q4 (1 Jan - 31 Mar).
    If so, renders a Streamlit warning banner about Section 135(5) unspent
    CSR funds and returns dynamic pitch-text modifiers for urgency framing.

    Returns:
        Q4AlertResult with flags and ready-to-use pitch text fragments.
    """
    today = today or _dt.date.today()
    is_q4 = today.month in Q4_MONTHS

    if is_q4:
        fy_end = _get_fy_end_date(today)
        days_left = (fy_end - today).days

        st.warning(
            f"⏰ **CSR Deadline Alert — {days_left} days left in FY**\n\n"
            f"Under **Section 135(5), Companies Act 2013**, any CSR amount "
            f"a company has not spent or earmarked for an ongoing project "
            f"by **31 March** must be transferred to a Schedule VII fund "
            f"(e.g. PM CARES) within 6 months. Companies with unspent "
            f"budgets have a strong incentive to disburse **now** rather "
            f"than forfeit the amount to a government fund.",
            icon="⚠️",
        )

        pitch_prefix = "URGENT — FY Closing Soon: "
        pitch_urgency_line = (
            f"With only {days_left} days left in this financial year, "
            f"deploying your remaining CSR budget with A Ray of Hope "
            f"Foundation ensures it directly reaches underprivileged "
            f"children in Pune — instead of lapsing to a Schedule VII "
            f"fund under Section 135(5)."
        )
        return Q4AlertResult(True, days_left, pitch_prefix, pitch_urgency_line)

    return Q4AlertResult(
        is_q4=False,
        days_to_fy_end=None,
        pitch_prefix="",
        pitch_urgency_line=(
            "Partnering now lets us plan a full-year education program "
            "together, rather than a rushed year-end disbursement."
        ),
    )


# ---------------------------------------------------------------------------
# 2. Statutory credential badge
# ---------------------------------------------------------------------------

def render_csr1_compliance_badge(location: str = "sidebar") -> None:
    """
    Renders the NGO's statutory registration credentials.

    Args:
        location: "sidebar" (default) renders in st.sidebar;
                   "main" renders inline in the main page body.
    """
    target = st.sidebar if location == "sidebar" else st

    verified_note = (
        f"Confirmed {NGO_CREDENTIALS['verified_as_of']}"
        if NGO_CREDENTIALS.get("verified_as_of")
        else "⚠️ Pending manual verification against MCA/IT Dept records"
    )

    target.markdown("### 📋 Statutory Compliance")
    target.info(
        f"""
**A Ray of Hope Foundation**

- **MCA CSR-1 Reg. No:** `{NGO_CREDENTIALS['csr1_reg_no']}`
- **80G Certificate ID:** `{NGO_CREDENTIALS['80g_cert_id']}`
- **12A Registration / Darpan ID:** `{NGO_CREDENTIALS['12a_reg_id']}`

_{verified_note}_
        """
    )


# ---------------------------------------------------------------------------
# 3. Impact economics per lakh
# ---------------------------------------------------------------------------

@dataclass
class ImpactMetrics:
    grant_amount_lakhs: float
    children_educated: int
    learning_kits: int
    learning_centers_equipped: float
    pitch_summary: str


def calculate_impact_metrics(grant_amount_lakhs: float) -> ImpactMetrics:
    """
    Converts a grant amount (in Lakhs INR) into tangible impact figures.

    Model (per ₹1 Lakh):
        25 children educated for 1 year + 1 digital learning kit + nutrition
        0.1 fully-equipped primary learning centers (i.e. 1 per ₹10L)

    Args:
        grant_amount_lakhs: Grant size in Lakhs (e.g. 10 for ₹10,00,000)

    Returns:
        ImpactMetrics dataclass with computed figures and a pitch-ready
        summary sentence.
    """
    if grant_amount_lakhs < 0:
        raise ValueError("grant_amount_lakhs must be non-negative")

    children = round(grant_amount_lakhs * CHILDREN_PER_LAKH)
    kits = round(grant_amount_lakhs * KITS_PER_LAKH)
    centers = round(grant_amount_lakhs * CENTERS_PER_LAKH, 1)

    amount_str = (
        f"₹{grant_amount_lakhs:g} Lakh" if grant_amount_lakhs != 1 else "₹1 Lakh"
    )

    if centers >= 1:
        centers_phrase = f"and equips {centers:g} primary learning centers"
    else:
        centers_phrase = f"and equips {centers:g} of a primary learning center"

    summary = (
        f"A {amount_str} grant directly supports {children} children "
        f"{centers_phrase} in Pune."
    )

    return ImpactMetrics(
        grant_amount_lakhs=grant_amount_lakhs,
        children_educated=children,
        learning_kits=kits,
        learning_centers_equipped=centers,
        pitch_summary=summary,
    )


# ---------------------------------------------------------------------------
# 4. Weighted pipeline forecasting
# ---------------------------------------------------------------------------

def calculate_weighted_pipeline(
    df: pd.DataFrame,
    grant_col: str = "target_grant_lakhs",
    prob_col: str = "win_probability",
) -> float:
    """
    Computes the probability-weighted expected yield of a pipeline.

    Total Expected Yield = Sum(target_grant_lakhs * win_probability)

    Args:
        df: DataFrame containing at minimum `grant_col` and `prob_col`.
            win_probability is expected as a fraction (0.0 - 1.0); values
            passed as 0-100 percentages are auto-normalized.
        grant_col: Column name holding grant size in Lakhs.
        prob_col: Column name holding win probability.

    Returns:
        Total expected yield in Lakhs INR, rounded to 2 decimals.
    """
    missing = [c for c in (grant_col, prob_col) if c not in df.columns]
    if missing:
        raise KeyError(f"DataFrame missing required column(s): {missing}")

    if df.empty:
        return 0.0

    probs = df[prob_col].astype(float)
    if probs.max() > 1:  # looks like a 0-100 scale, normalize
        probs = probs / 100.0

    weighted_yield = (df[grant_col].astype(float) * probs).sum()
    return round(float(weighted_yield), 2)