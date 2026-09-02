import re
import urllib.parse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pdfplumber
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import database as db
from modules import compliance_engine as ce

# ----------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ----------------------------------------------------------------------------
FUNNEL_STAGES = ["New Lead", "Contacted", "In Discussion", "Pitch Sent", "Funded"]
SLA_TRIGGER_STATUSES = {"Contacted", "Pitch Sent"}
SLA_THRESHOLD_DAYS = 14

ZONE_PROXIMITY_SCORES = {
    "Hinjawadi": 95,
    "Kharadi": 95,
    "Baner": 90,
    "Wakad": 88,
    "Viman Nagar": 85,
    "Pimpri": 82,
    "Chinchwad": 80,
    "Bhosari MIDC": 78,
    "Chakan": 65,
    "Talegaon": 60,
    "Ranjangaon": 55,
}
DEFAULT_PROXIMITY_SCORE = 40

CSR_FOCUS_OPTIONS = [
    "Education", "Healthcare", "Skill Development", "Scholarship", "Livelihood", "Other"
]

KEYWORDS = [
    "Education", "Unspent CSR", "Allocation", "Scholarship", "Pune",
    "Skill Development", "Healthcare", "Livelihood",
]

MONEY_PATTERN = re.compile(
    r'(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d+)?\s?(?:Lakh|Lakhs|Crore|Crores)?',
    re.IGNORECASE,
)

# ----------------------------------------------------------------------------
# PAGE SETUP & COMPLIANCE BADGES
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="A Ray of Hope Foundation - CSR Portal",
    page_icon="🤝",
    layout="wide",
)

try:
    db.init_db()
    db.seed_data()
except Exception:
    pass

# Render Sidebar Statutory Credentials & Top-Page Urgency Banner
ce.render_csr1_compliance_badge(location="sidebar")
q4_alert = ce.render_march31_alert()

st.title("A Ray of Hope Foundation — CSR Corporate Outreach Portal")
st.markdown(
    "Track, manage, and grow corporate partnerships across Pune to fund education programs."
)

# ----------------------------------------------------------------------------
# DATA ENGINE LOADERS
# ----------------------------------------------------------------------------
@st.cache_data(ttl=5)
def load_companies() -> pd.DataFrame:
    raw_data = db.get_all_companies()
    df = pd.DataFrame(raw_data) if not isinstance(raw_data, pd.DataFrame) else raw_data.copy()

    if df.empty:
        return pd.DataFrame(columns=[
            "id", "company_name", "zone", "csr_focus", "contact_person",
            "designation", "email", "linkedin_url", "csr_budget_lakhs",
            "target_grant_lakhs", "win_probability", "last_contacted_date",
            "financial_year", "status", "last_notes"
        ])

    # Normalize defaults & data types
    df["target_grant_lakhs"] = df["target_grant_lakhs"].fillna(10.0).astype(float)
    df["csr_budget_lakhs"] = df["csr_budget_lakhs"].fillna(100.0).astype(float)
    df["win_probability"] = df["win_probability"].fillna(0.20).astype(float)
    
    # Process dates for SLA tracking
    now = datetime.now()
    df["last_contacted_date"] = pd.to_datetime(df["last_contacted_date"]).fillna(now)

    return df

def refresh_data():
    load_companies.clear()

df = load_companies()

# ----------------------------------------------------------------------------
# CORE COMPUTATIONAL HELPERS
# ----------------------------------------------------------------------------
def compute_sla_flag(row: pd.Series, today: datetime = None) -> pd.Series:
    today = today or datetime.now()
    last_contact = pd.to_datetime(row["last_contacted_date"])
    days_since = (today - last_contact).days

    is_overdue = (row["status"] in SLA_TRIGGER_STATUSES) and (days_since > SLA_THRESHOLD_DAYS)
    badge = "⚠️ Follow-up Overdue" if is_overdue else "✅ On Track"
    return pd.Series({"days_since_contact": days_since, "is_overdue": is_overdue, "sla_badge": badge})

def compute_proximity_score(zone: str) -> int:
    return ZONE_PROXIMITY_SCORES.get(zone, DEFAULT_PROXIMITY_SCORE)

def enrich_lead_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    sla_fields = df.apply(compute_sla_flag, axis=1)
    df = pd.concat([df, sla_fields], axis=1)
    df["proximity_score"] = df["zone"].apply(compute_proximity_score)
    return df

def extract_pdf_insights(uploaded_file):
    insights = {"keyword_hits": {}, "raw_snippets": [], "amounts_found": []}
    try:
        full_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
    except Exception as e:
        st.error(f"Could not parse PDF: {e}")
        return insights

    if not full_text.strip():
        st.warning("No extractable text found in PDF.")
        return insights

    for kw in KEYWORDS:
        matches = [m.start() for m in re.finditer(re.escape(kw), full_text, re.IGNORECASE)]
        if matches:
            insights["keyword_hits"][kw] = len(matches)
            first_idx = matches[0]
            snippet = full_text[max(0, first_idx - 80): first_idx + 120].replace("\n", " ").strip()
            insights["raw_snippets"].append(f"[{kw}] ...{snippet}...")

    insights["amounts_found"] = sorted(set(MONEY_PATTERN.findall(full_text)))[:15]
    return insights

# ----------------------------------------------------------------------------
# MAIN TABS ARCHITECTURE
# ----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📋 Lead Directory & SLA Tracker", "✉️ Custom Pitch Generator", "📊 Visual Analytics"])

# ============================================================================
# TAB 1: LEAD DIRECTORY & SLA TRACKER
# ============================================================================
with tab1:
    enriched_df = enrich_lead_data(df)
    
    if enriched_df.empty:
        st.info("No corporate leads in the database.")
    else:
        overdue_count = int(enriched_df["is_overdue"].sum())
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Leads", len(enriched_df))
        col2.metric("⚠️ Follow-ups Overdue", overdue_count)
        col3.metric("Avg. Pune Proximity Score", f"{enriched_df['proximity_score'].mean():.0f}%")
        col4.metric("Weighted Pipeline Yield", f"₹{ce.calculate_weighted_pipeline(enriched_df):.1f}L")

        st.divider()

        col_filter, col_main = st.columns([1, 3])

        with col_filter:
            st.subheader("🔍 Filters")
            zones = ["All"] + sorted(enriched_df["zone"].unique().tolist())
            selected_zone = st.selectbox("Zone", zones)
            
            selected_status = st.selectbox("Status", ["All"] + FUNNEL_STAGES)
            overdue_only = st.checkbox("Show Overdue Only", value=False)
            search_term = st.text_input("Search Company / Contact")

            if st.button("🔄 Refresh Data", use_container_width=True):
                refresh_data()
                st.rerun()

        filtered_df = enriched_df.copy()
        if selected_zone != "All":
            filtered_df = filtered_df[filtered_df["zone"] == selected_zone]
        if selected_status != "All":
            filtered_df = filtered_df[filtered_df["status"] == selected_status]
        if overdue_only:
            filtered_df = filtered_df[filtered_df["is_overdue"]]
        if search_term:
            term = search_term.strip().lower()
            filtered_df = filtered_df[
                filtered_df["company_name"].str.lower().str.contains(term, na=False)
                | filtered_df["contact_person"].str.lower().str.contains(term, na=False)
            ]

        with col_main:
            st.subheader("📋 Corporate Directory")

            def highlight_overdue(row):
                is_ov = row.get("sla_badge") == "⚠️ Follow-up Overdue"
                return ["background-color: #ffe1e1" if is_ov else ""] * len(row)

            display_cols = [
                "id", "company_name", "zone", "status", "sla_badge",
                "days_since_contact", "proximity_score", "target_grant_lakhs"
            ]

            styled = (
                filtered_df[display_cols]
                .style
                .apply(highlight_overdue, axis=1)
                .format({
                    "target_grant_lakhs": "₹{:.0f}L",
                    "proximity_score": "{}%",
                })
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Lead Update Form
            st.markdown("---")
            st.markdown("**Update Lead Status**")
            id_to_name = dict(zip(filtered_df["id"], filtered_df["company_name"]))
            
            if id_to_name:
                selected_id = st.selectbox("Select Company", options=list(id_to_name.keys()), format_func=lambda x: f"{x} - {id_to_name[x]}")
                current_status = filtered_df.loc[filtered_df["id"] == selected_id, "status"].values[0]
                
                with st.form("update_lead_form"):
                    new_status = st.selectbox("New Status", options=FUNNEL_STAGES, index=FUNNEL_STAGES.index(current_status) if current_status in FUNNEL_STAGES else 0)
                    update_notes = st.text_area("Quick Notes", placeholder="Add progress notes...")
                    if st.form_submit_button("💾 Save Update"):
                        try:
                            db.update_company_status(selected_id, new_status, update_notes)
                            st.success(f"Updated status to '{new_status}'!")
                            refresh_data()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update lead: {e}")

# ============================================================================
# TAB 2: CUSTOM PITCH GENERATOR & COMPLIANCE ENGINE
# ============================================================================
with tab2:
    st.subheader("Custom CSR Pitch Generator & Grant Calculator")

    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("**1. Document Intelligence (Optional)**")
        uploaded_file = st.file_uploader("Upload CSR Annual Report or BRSR (PDF)", type=["pdf"])
        pdf_insights = None
        if uploaded_file is not None:
            with st.spinner("Extracting insights..."):
                pdf_insights = extract_pdf_insights(uploaded_file)
            if pdf_insights["keyword_hits"]:
                st.success("Keywords Found: " + ", ".join(pdf_insights["keyword_hits"].keys()))

        st.markdown("**2. Recipient Information**")
        company_names = df["company_name"].tolist() if not df.empty else []
        selected_company_name = st.selectbox("Select Existing Lead", options=["Custom Lead"] + company_names)

        if selected_company_name != "Custom Lead":
            row = df[df["company_name"] == selected_company_name].iloc[0]
            comp_name = row["company_name"]
            contact_name = row.get("contact_person", "")
            contact_email = row.get("email", "")
            csr_focus = row.get("csr_focus", "Education")
            grant_val = float(row.get("target_grant_lakhs", 10.0))
        else:
            comp_name = st.text_input("Company Name")
            contact_name = st.text_input("Contact Person")
            contact_email = st.text_input("Email")
            csr_focus = st.selectbox("CSR Focus Area", CSR_FOCUS_OPTIONS)
            grant_val = 10.0

        st.markdown("**3. Grant Impact Model**")
        grant_ask = st.slider("Grant Request (₹ Lakhs)", min_value=1.0, max_value=50.0, value=grant_val)
        
        # Calculate impact metrics using modules/compliance_engine
        impact = ce.calculate_impact_metrics(grant_ask)
        st.info(f"💡 Impact: {impact.pitch_summary}")

    with c_right:
        st.markdown("**Generated Pitch Draft**")
        
        pitch_urgency = q4_alert.pitch_urgency_line if q4_alert.is_q4 else ""
        
        subject = f"CSR Partnership Proposal — {csr_focus} | A Ray of Hope Foundation"
        body = f"""Dear {contact_name or 'Sir/Madam'},

I hope this email finds you well.

I am reaching out on behalf of A Ray of Hope Foundation regarding {comp_name}'s CSR focus on {csr_focus}. 

{q4_alert.pitch_prefix}{impact.pitch_summary} {pitch_urgency}

Statutory Compliance Credentials:
- MCA Form CSR-1 Reg No: {ce.NGO_CREDENTIALS['csr1_reg_no']}
- 80G Tax Exemption Certificate: {ce.NGO_CREDENTIALS['80g_cert_id']}

We would welcome a brief 15-minute call to share our detailed impact proposal.

Warm regards,
A Ray of Hope Foundation Team
Pune, Maharashtra
"""
        st.text_input("Subject", value=subject)
        edited_body = st.text_area("Body", value=body, height=320)

        if contact_email:
            mailto_link = (
                f"mailto:{urllib.parse.quote(contact_email)}"
                f"?subject={urllib.parse.quote(subject)}"
                f"&body={urllib.parse.quote(edited_body)}"
            )
            st.link_button("📤 Open in Local Mail Client", mailto_link, use_container_width=True)

        if st.button("✅ Mark as Pitch Sent & Log Activity", use_container_width=True):
            if selected_company_name != "Custom Lead":
                c_id = df[df["company_name"] == selected_company_name].iloc[0]["id"]
                db.update_company_status(c_id, "Pitch Sent", f"Pitch sent for ₹{grant_ask}L ask.")
                st.success(f"Updated status for {selected_company_name} to 'Pitch Sent'!")
                refresh_data()
                st.rerun()

# ============================================================================
# TAB 3: VISUAL ANALYTICS
# ============================================================================
with tab3:
    st.subheader("📊 Visual Analytics & Pipeline Forecast")

    if df.empty:
        st.info("No analytics data available.")
    else:
        col_analytics_1, col_analytics_2 = st.columns([1.1, 1])

        with col_analytics_1:
            # Conversion Funnel Chart
            stage_index = {s: i for i, s in enumerate(FUNNEL_STAGES)}
            temp_df = df.copy()
            temp_df["stage_idx"] = temp_df["status"].map(stage_index).fillna(0)

            counts = [int((temp_df["stage_idx"] >= i).sum()) for i in range(len(FUNNEL_STAGES))]

            fig_funnel = go.Figure(
                go.Funnel(
                    y=FUNNEL_STAGES,
                    x=counts,
                    textposition="inside",
                    textinfo="value+percent initial",
                    marker={"color": ["#0B5FFF", "#3D7EFF", "#6FA0FF", "#A3C4FF", "#1FA774"]},
                )
            )
            fig_funnel.update_layout(title="Lead Conversion Funnel", height=380)
            st.plotly_chart(fig_funnel, use_container_width=True)

        with col_analytics_2:
            # Pipeline Gauge Chart
            active = df[df["status"] != "Funded"]
            raw_total = active["target_grant_lakhs"].sum()
            weighted_total = (active["target_grant_lakhs"] * active["win_probability"]).sum()

            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=weighted_total,
                    number={"prefix": "₹", "suffix": "L", "valueformat": ".1f"},
                    delta={"reference": raw_total, "relative": False, "valueformat": ".1f"},
                    title={"text": "Weighted Pipeline Yield vs Raw Target (₹ Lakhs)"},
                    gauge={
                        "axis": {"range": [0, max(raw_total, 1) * 1.1]},
                        "bar": {"color": "#0B5FFF"},
                    },
                )
            )
            fig_gauge.update_layout(height=380)
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.divider()

        # Zone Distribution Bar Chart
        zone_counts = df.groupby("zone", as_index=False)["target_grant_lakhs"].sum()
        fig_zone = px.bar(
            zone_counts,
            x="zone",
            y="target_grant_lakhs",
            color="zone",
            labels={"target_grant_lakhs": "Target Grant Ask (₹ Lakhs)", "zone": "Zone"},
            title="CSR Target Ask Distribution by Pune Industrial Zone",
        )
        st.plotly_chart(fig_zone, use_container_width=True)