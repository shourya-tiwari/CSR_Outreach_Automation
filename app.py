"""
app.py
-------
Main Streamlit application for A Ray of Hope Foundation's CSR Corporate
Outreach & Lead Tracker.

Wires together the five backend modules:
    config.py              - static reference data, validation, env config
    database.py             - SQLite data-access layer
    compliance_engine.py    - CSR-1/80G/12A badges, Q4 urgency, pipeline/impact math
    scraper.py               - live web scraping of corporate contact pages
    enrichment.py            - MCA master-data parsing + Hunter/Apollo enrichment

Layout:
    Sidebar   - compliance badges + Q4 urgency status
    Tab 1     - Directory & SLA Tracker
    Tab 2     - Scraper & Pitch Generator
    Tab 3     - Visual Analytics (Plotly)
"""

from __future__ import annotations

import re
import io
import urllib.parse
from datetime import date, datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import config
import database as db
import compliance_engine as ce
import scraper
import enrichment

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(page_title=config.APP_NAME, page_icon=config.APP_ICON, layout="wide")

db.init_db()


# ============================================================================
# DATA LOADING (cached, invalidated after any write)
# ============================================================================
@st.cache_data(ttl=15, show_spinner=False)
def load_companies_df() -> pd.DataFrame:
    return db.get_all_companies_df()


def refresh_and_rerun():
    st.cache_data.clear()
    st.rerun()


# ============================================================================
# HEURISTIC SCORING HELPERS (local to the UI layer — not business-critical math)
# ============================================================================

# Approximate straight-line distance (km) from central Pune to each target
# zone, used ONLY to rank outreach priority. These are illustrative
# estimates for relative sorting, not surveyed/geocoded distances — swap in
# real geocoding (e.g. a Maps API) if precise figures are ever needed.
_ZONE_APPROX_DISTANCE_KM = {
    "Hinjawadi Phase 1": 18, "Hinjawadi Phase 2": 20, "Hinjawadi Phase 3": 22,
    "Kharadi (EON IT Park)": 12, "Bhosari MIDC": 15, "Chakan Industrial Area": 28,
    "Pimpri-Chinchwad": 16, "Magarpatta": 8, "Viman Nagar": 9, "Baner": 12,
}
_DEFAULT_ZONE_DISTANCE_KM = 25  # fallback for unmapped/scraped zone strings

# CSR focus areas most directly aligned with the NGO's core mission
_CORE_FOCUS_AREAS = {
    "Primary Education & Literacy", "Child Welfare & Nutrition",
    "Community Learning Centers", "School Infrastructure", "Girl Child Education",
}
_SECONDARY_FOCUS_AREAS = {
    "Digital Literacy / EdTech", "STEM Education",
    "Special Needs / Inclusive Education", "Teacher Training & Capacity Building",
}


def compute_proximity_score(zone: str, csr_focus: str) -> int:
    """
    Heuristic 0-100 lead-priority score blending geographic proximity to
    Pune (logistics ease) and CSR-focus alignment with the NGO's mission.
    This is a prioritization aid for the outreach team, not a precise metric.
    """
    distance_km = _ZONE_APPROX_DISTANCE_KM.get(zone, _DEFAULT_ZONE_DISTANCE_KM)
    distance_score = max(0, 100 - distance_km * 2.5)

    if csr_focus in _CORE_FOCUS_AREAS:
        focus_score = 100
    elif csr_focus in _SECONDARY_FOCUS_AREAS:
        focus_score = 75
    else:
        focus_score = 50

    return round(0.5 * distance_score + 0.5 * focus_score)


def days_since(date_str: Optional[str]) -> Optional[int]:
    """Days elapsed since a stored ISO date string. None if unset/unparseable."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        d = datetime.fromisoformat(date_str.split("T")[0]).date()
        return (date.today() - d).days
    except ValueError:
        return None


SLA_BREACH_DAYS = 14  # flag active leads with no contact in this many days


# ============================================================================
# SIDEBAR — Compliance badges + Q4 urgency
# ============================================================================
def render_sidebar():
    st.sidebar.markdown(f"## {config.APP_ICON} {config.ORG_NAME}")
    st.sidebar.caption(f"{config.ORG_CITY} · CSR Corporate Outreach Portal")

    st.sidebar.markdown("### 📋 Statutory Compliance")
    for badge in ce.get_compliance_badges():
        st.sidebar.markdown(badge.render_markdown())

    st.sidebar.divider()

    st.sidebar.markdown("### ⏰ Financial Year Status")
    urgency = ce.calculate_q4_urgency()
    urgency_render = urgency.render_markdown()

    if urgency.level == "critical":
        st.sidebar.error(urgency_render)
    elif urgency.level == "high":
        st.sidebar.warning(urgency_render)
    elif urgency.level == "moderate":
        st.sidebar.info(urgency_render)
    else:
        st.sidebar.success(urgency_render)

    if urgency.level in ("critical", "high"):
        st.sidebar.caption(
            "Section 135(5): unspent CSR funds not tied to an ongoing project "
            "must transfer to a Schedule VII fund if not spent by FY close — "
            "use this window to push pending pitches."
        )


# ============================================================================
# TAB 1 — Directory & SLA Tracker
# ============================================================================
def render_directory_tab():
    st.subheader("📇 Corporate Lead Directory")

    df = load_companies_df()
    if df.empty:
        st.info("No leads yet. Add companies via the Scraper tab or your seed script.")
        return

    # --- Filters -------------------------------------------------------
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        zone_filter = st.selectbox("Zone", config.ZONE_FILTER_OPTIONS, key="zone_filter")
    with col2:
        status_filter = st.selectbox("Status", ["All"] + config.LEAD_STATUSES, key="status_filter")
    with col3:
        search_query = st.text_input(
            "🔎 Search company or contact name", key="lead_search", placeholder="e.g. Infosys, Priya Nair"
        )

    filtered = df.copy()
    if zone_filter != "All":
        filtered = filtered[filtered["zone"] == zone_filter]
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]
    if search_query:
        q = search_query.strip().lower()
        filtered = filtered[
            filtered["company_name"].astype(str).str.lower().str.contains(q, na=False)
            | filtered["contact_person"].astype(str).str.lower().str.contains(q, na=False)
        ]

    if filtered.empty:
        st.warning("No leads match the current filters.")
        return

    # --- Derived columns -------------------------------------------------
    filtered["proximity_score"] = filtered.apply(
        lambda r: compute_proximity_score(r.get("zone", ""), r.get("csr_focus", "")), axis=1
    )
    filtered["days_since_contact"] = filtered["last_contacted_date"].apply(days_since)
    filtered["sla_flag"] = filtered.apply(
        lambda r: "⚠️ SLA Breach"
        if (
            r["status"] in config.ACTIVE_PIPELINE_STATUSES
            and (r["days_since_contact"] is None or r["days_since_contact"] > SLA_BREACH_DAYS)
        )
        else "✅ On track",
        axis=1,
    )
    filtered["email_link"] = filtered["email"].apply(lambda e: f"mailto:{e}" if e else "")
    if "phone" not in filtered.columns:
        filtered["phone"] = ""
    filtered["phone_link"] = filtered["phone"].apply(lambda p: f"tel:{p}" if p else "")

    display_cols = [
        "id", "company_name", "zone", "csr_focus", "contact_person", "designation",
        "email_link", "phone_link", "status", "proximity_score",
        "days_since_contact", "sla_flag",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].sort_values("proximity_score", ascending=False),
        width='stretch',
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "company_name": st.column_config.TextColumn("Company"),
            "zone": st.column_config.TextColumn("Zone"),
            "csr_focus": st.column_config.TextColumn("CSR Focus"),
            "contact_person": st.column_config.TextColumn("Contact"),
            "designation": st.column_config.TextColumn("Designation"),
            "email_link": st.column_config.LinkColumn("Email", display_text=r"mailto:(.*)"),
            "phone_link": st.column_config.LinkColumn("Phone", display_text=r"tel:(.*)"),
            "status": st.column_config.TextColumn("Status"),
            "proximity_score": st.column_config.ProgressColumn(
                "Priority Score", min_value=0, max_value=100, format="%d"
            ),
            "days_since_contact": st.column_config.NumberColumn("Days Since Contact"),
            "sla_flag": st.column_config.TextColumn("SLA"),
        },
    )

    st.caption(
        f"{len(filtered)} lead(s) shown · Priority Score blends zone proximity to Pune "
        f"and CSR-focus alignment (heuristic, for prioritization only)."
    )

    st.divider()

    # --- Status update form ----------------------------------------------
    st.markdown("#### ✏️ Update Lead Status")
    with st.form("status_update_form", clear_on_submit=True):
        lead_options = {
            f"{row.id} — {row.company_name} ({row.status})": row.id
            for row in filtered.itertuples()
        }
        selected_label = st.selectbox("Select lead", list(lead_options.keys()))
        new_status = st.selectbox("New status", config.LEAD_STATUSES)
        notes = st.text_area("Notes", placeholder="What happened in this interaction?")
        submitted = st.form_submit_button("Update Status", type="primary")

        if submitted:
            company_id = lead_options[selected_label]
            try:
                db.update_company_status(company_id, new_status, notes)
                st.success(f"Updated lead #{company_id} to '{new_status}'.")
                refresh_and_rerun()
            except ValueError as e:
                st.error(str(e))


# ============================================================================
# TAB 2 — Scraper & Pitch Generator
# ============================================================================

def render_scraper_tab():
    st.subheader("🕸️ Live Scraper")
    st.caption(
        "Crawls a company's public /csr, /sustainability, and /contact-us pages "
        "for emails, phone numbers, and LinkedIn URLs, then adds a qualified lead."
    )

    with st.form("scraper_form"):
        sc1, sc2 = st.columns(2)
        with sc1:
            target_name = st.text_input("Company name", placeholder="e.g. Persistent Systems")
            target_zone = st.selectbox("Zone", config.PUNE_ZONES)
        with sc2:
            target_url = st.text_input("Website URL", placeholder="https://www.example.com")
            target_focus = st.selectbox("CSR Focus", config.CSR_FOCUS_AREAS)

        run_scrape = st.form_submit_button("🕷️ Run Scraper", type="primary")

    if run_scrape:
        if not target_name or not target_url:
            st.error("Company name and URL are required.")
        else:
            with st.spinner(f"Crawling {target_url}... this respects robots.txt and rate limits, so it may take a moment."):
                summary = scraper.run_scraper(
                    [{"company_name": target_name, "url": target_url,
                      "zone": target_zone, "csr_focus": target_focus}],
                    default_zone=target_zone,
                    default_csr_focus=target_focus,
                )
            st.json(summary)
            if summary["inserted"] > 0:
                st.success(f"Added {target_name} to the pipeline.")
                refresh_and_rerun()
            elif summary["skipped_duplicate"] > 0:
                st.warning("This domain is already in your database.")
            else:
                st.info("No public contact details were found on the crawled pages.")

    st.divider()

    # --- Enrichment ---------------------------------------------------
    st.markdown("#### 🔍 Enrich a Domain (Hunter.io / Apollo.io)")
    st.caption("Finds verified names/emails for CSR Manager, Company Secretary, etc. Requires an API key set as an environment variable.")
    enrich_col1, enrich_col2 = st.columns([3, 1])
    with enrich_col1:
        enrich_domain_input = st.text_input("Company domain", placeholder="e.g. persistent.com", key="enrich_domain")
    with enrich_col2:
        provider = st.selectbox("Provider", ["hunter", "apollo"], label_visibility="collapsed")

    if st.button("Find CSR Contacts"):
        if not enrich_domain_input:
            st.error("Enter a domain first.")
        else:
            try:
                with st.spinner("Querying enrichment provider..."):
                    contacts = enrichment.enrich_domain(enrich_domain_input, prefer=provider)
                if contacts:
                    contacts_df = pd.DataFrame([c.__dict__ for c in contacts])
                    st.dataframe(contacts_df, width='stretch', hide_index=True)
                else:
                    st.info("No matching CSR-relevant contacts found for this domain.")
            except EnvironmentError as e:
                st.error(str(e))

    st.divider()

    # --- PDF annual report keyword parser -------------------------------
    st.markdown("#### 📄 Annual Report Keyword Scanner")
    st.caption("Upload a company's Annual Report PDF to surface CSR budget mentions and relevant passages.")

    uploaded_pdf = st.file_uploader("Upload Annual Report (PDF)", type=["pdf"])
    if uploaded_pdf is not None:
        with st.spinner("Extracting text..."):
            findings = scan_pdf_for_csr_keywords(uploaded_pdf)

        if findings["error"]:
            st.error(findings["error"])
        else:
            st.write(f"**Pages scanned:** {findings['page_count']}")
            m1, m2 = st.columns(2)
            m1.metric("CSR mentions", findings["keyword_counts"].get("csr", 0))
            m2.metric("Currency amounts found", len(findings["money_mentions"]))

            if findings["money_mentions"]:
                st.markdown("**Budget-related figures found:**")
                st.write(", ".join(findings["money_mentions"][:20]))

            if findings["matched_sentences"]:
                with st.expander(f"View {len(findings['matched_sentences'])} matching passages"):
                    for sentence in findings["matched_sentences"][:25]:
                        st.markdown(f"- {sentence}")
            else:
                st.info("No CSR-related passages detected.")

    st.divider()

    # --- Pitch generator --------------------------------------------------
    render_pitch_generator()


CSR_KEYWORDS = [
    "csr", "corporate social responsibility", "section 135", "schedule vii",
    "underprivileged", "education", "community development", "csr-1",
    "unspent csr", "csr committee",
]


def scan_pdf_for_csr_keywords(uploaded_file) -> dict:
    """Extracts text from an uploaded PDF and surfaces CSR-relevant
    passages and currency figures. Returns a results dict; never raises."""
    result = {"error": None, "page_count": 0, "keyword_counts": {}, "money_mentions": [], "matched_sentences": []}

    try:
        from pypdf import PdfReader
    except ImportError:
        result["error"] = "pypdf is not installed. Run: pip install pypdf"
        return result

    try:
        reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        result["page_count"] = len(reader.pages)
        full_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        result["error"] = f"Could not read PDF: {e}"
        return result

    if not full_text.strip():
        result["error"] = "No extractable text found — this may be a scanned/image-only PDF."
        return result

    lower_text = full_text.lower()
    result["keyword_counts"] = {"csr": lower_text.count("csr")}

    # Currency figures using the same money pattern style as config.py
    money_pattern = re.compile(
        r"₹\s?[\d,]+(?:\.\d+)?\s?(?:lakhs?|crores?|cr|l)\b", re.IGNORECASE
    )
    result["money_mentions"] = sorted(set(m.group(0).strip() for m in money_pattern.finditer(full_text)))

    sentences = re.split(r"(?<=[.!?])\s+", full_text)
    result["matched_sentences"] = [
        s.strip().replace("\n", " ")
        for s in sentences
        if any(k in s.lower() for k in CSR_KEYWORDS) and 20 < len(s.strip()) < 400
    ]

    return result


def render_pitch_generator():
    st.markdown("#### ✉️ Pitch Draft Generator")

    df = load_companies_df()
    manual_entry = "— Enter manually —"
    options = [manual_entry] + (
        [f"{r.id} — {r.company_name}" for r in df.itertuples()] if not df.empty else []
    )
    selection = st.selectbox("Recipient", options)

    if selection != manual_entry:
        row = df[df["id"] == int(selection.split(" — ")[0])].iloc[0]
        recipient_name = row.get("contact_person") or "Team"
        recipient_email = row.get("email") or ""
        recipient_company = row.get("company_name")
    else:
        pc1, pc2 = st.columns(2)
        with pc1:
            recipient_name = st.text_input("Recipient name", value="Team")
            recipient_company = st.text_input("Company name")
        with pc2:
            recipient_email = st.text_input("Recipient email")

    grant_ask_lakhs = st.number_input("Grant ask (₹ Lakhs)", min_value=0.5, value=10.0, step=0.5)

    impact = ce.estimate_impact(grant_ask_lakhs)
    urgency = ce.calculate_q4_urgency()

    urgency_line = ""
    if urgency.level in ("critical", "high"):
        urgency_line = (
            f"\n\nWith {urgency.days_remaining} days left in {urgency.fy_label}, deploying this "
            f"now ensures your CSR budget reaches these children directly rather than lapsing "
            f"to a Schedule VII fund under Section 135(5)."
        )

    default_subject = f"Partnership Proposal: {config.ORG_NAME} x {recipient_company or '[Company]'}"
    default_body = (
        f"Dear {recipient_name},\n\n"
        f"I'm reaching out on behalf of {config.ORG_NAME}, a CSR-1 registered NGO in "
        f"{config.ORG_CITY} focused on educating underprivileged children.\n\n"
        f"A grant of ₹{grant_ask_lakhs:g} Lakh would support an estimated "
        f"{impact.estimated_children_reached} children for a full year of schooling, "
        f"learning materials, and nutrition support.{urgency_line}\n\n"
        f"I'd welcome the chance to share our program details and impact reports at your "
        f"convenience.\n\n"
        f"Warm regards,\nOutreach Team\n{config.ORG_NAME}"
    )

    subject = st.text_input("Subject", value=default_subject)
    body = st.text_area("Email body (editable)", value=default_body, height=280)

    if recipient_email:
        mailto_url = (
            f"mailto:{recipient_email}"
            f"?subject={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(body)}"
        )
        st.link_button("✉️ Open in Email Client", mailto_url)
    else:
        st.caption("Enter a recipient email to generate a mailto: link.")


# ============================================================================
# TAB 3 — Visual Analytics
# ============================================================================
def render_analytics_tab():
    st.subheader("📊 Visual Analytics")

    df = load_companies_df()
    if df.empty:
        st.info("No data yet — analytics will appear once leads are added.")
        return

    companies = df.to_dict("records")
    summary = ce.calculate_pipeline_summary(companies)
    impact = ce.calculate_total_impact(companies)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads", summary.total_leads)
    m2.metric("Active Pipeline", summary.active_leads)
    m3.metric("Weighted Pipeline (₹L)", summary.weighted_pipeline_lakhs)
    m4.metric("Children Reached (Funded)", impact["estimated_children_reached"])

    col_a, col_b = st.columns(2)

    # --- Funnel chart ------------------------------------------------
    with col_a:
        funnel_order = [
            "New Lead", "Contacted", "In Discussion", "Proposal Sent",
            "Pitch Sent", "Due Diligence", "Funded",
        ]
        funnel_counts = [int((df["status"] == s).sum()) for s in funnel_order]

        fig_funnel = go.Figure(
            go.Funnel(y=funnel_order, x=funnel_counts, textinfo="value+percent initial")
        )
        fig_funnel.update_layout(title="Lead Conversion Funnel", height=420)
        st.plotly_chart(fig_funnel, width='stretch')

    # --- Gauge: weighted pipeline vs target --------------------------
    with col_b:
        target_lakhs = st.number_input(
            "Annual fundraising target (₹ Lakhs)", min_value=10.0, value=500.0, step=10.0
        )
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=summary.weighted_pipeline_lakhs,
                delta={"reference": target_lakhs},
                title={"text": "Weighted Pipeline Yield vs Target (₹ Lakhs)"},
                gauge={
                    "axis": {"range": [0, max(target_lakhs * 1.2, summary.weighted_pipeline_lakhs * 1.1, 1)]},
                    "bar": {"color": "darkgreen"},
                    "threshold": {
                        "line": {"color": "red", "width": 3},
                        "thickness": 0.8,
                        "value": target_lakhs,
                    },
                },
            )
        )
        fig_gauge.update_layout(height=420)
        st.plotly_chart(fig_gauge, width='stretch')

    # --- Bar chart: CSR ask by zone ------------------------------------
    zone_summary = (
        df.groupby("zone", dropna=False)["target_grant_lakhs"]
        .sum(min_count=1)
        .fillna(0)
        .reset_index()
        .sort_values("target_grant_lakhs", ascending=False)
    )
    fig_bar = px.bar(
        zone_summary, x="zone", y="target_grant_lakhs",
        title="CSR Target Ask by Pune Industrial Zone (₹ Lakhs)",
        labels={"zone": "Zone", "target_grant_lakhs": "Target Ask (₹L)"},
    )
    fig_bar.update_layout(height=420, xaxis_tickangle=-30)
    st.plotly_chart(fig_bar, width='stretch')

    st.caption(
        f"Conversion rate: {summary.conversion_rate_pct}% · "
        f"Funded to date: ₹{summary.funded_lakhs}L · "
        f"Est. cost/child: ₹{impact['cost_per_child_inr']:,.0f}/yr"
    )


# ============================================================================
# MAIN
# ============================================================================
def main():
    render_sidebar()

    st.title(f"{config.APP_ICON} {config.APP_NAME}")
    st.caption(f"{config.ORG_NAME} · {config.ORG_CITY} · {ce.compliance_summary_line()}")

    tab1, tab2, tab3 = st.tabs([
        "📇 Directory & SLA Tracker",
        "🕸️ Scraper & Pitch Generator",
        "📊 Visual Analytics",
    ])

    with tab1:
        render_directory_tab()
    with tab2:
        render_scraper_tab()
    with tab3:
        render_analytics_tab()


if __name__ == "__main__":
    main()