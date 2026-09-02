import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px
from database import init_db, seed_data, get_all_companies, add_company, update_company_status

# ----------------------------------------------------------------------------
# PAGE CONFIGURATION & INITIALIZATION
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="A Ray of Hope Foundation - CSR Portal",
    page_icon="🤝",
    layout="wide",
)

# Ensure database table and sample records exist
try:
    init_db()
    seed_data()
except Exception:
    pass

ZONES = ["All", "Hinjawadi", "Kharadi", "Bhosari MIDC", "Chakan", "Pimpri", "Chinchwad"]
STATUSES = [
    "New Lead",
    "Contacted",
    "In Discussion",
    "Pitch Sent",
    "Funded",
    "Not Interested",
    "Declined",
]

CONTACTED_STATUSES = {"Contacted", "In Discussion", "Pitch Sent", "Funded"}
DISCUSSION_STATUSES = {"In Discussion"}
PITCH_OR_FUNDED_STATUSES = {"Pitch Sent", "Funded"}


# ----------------------------------------------------------------------------
# DATA LOADERS & HELPER FUNCTIONS
# ----------------------------------------------------------------------------
@st.cache_data(ttl=5)
def load_companies() -> pd.DataFrame:
    """Fetch all companies from SQLite and normalize into a standardized DataFrame."""
    raw_data = get_all_companies()
    
    if isinstance(raw_data, pd.DataFrame):
        df = raw_data.copy()
    else:
        df = pd.DataFrame(raw_data)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "id", "company_name", "name", "zone", "csr_focus",
                "contact_person", "designation", "email", "linkedin_url",
                "linkedin", "status", "last_notes", "notes"
            ]
        )

    # Normalize column aliases so both source schemas work seamlessly
    if "company_name" in df.columns and "name" not in df.columns:
        df["name"] = df["company_name"]
    elif "name" in df.columns and "company_name" not in df.columns:
        df["company_name"] = df["name"]

    if "linkedin_url" in df.columns and "linkedin" not in df.columns:
        df["linkedin"] = df["linkedin_url"]
    elif "linkedin" in df.columns and "linkedin_url" not in df.columns:
        df["linkedin_url"] = df["linkedin"]

    if "last_notes" in df.columns and "notes" not in df.columns:
        df["notes"] = df["last_notes"]
    elif "notes" in df.columns and "last_notes" not in df.columns:
        df["last_notes"] = df["notes"]

    return df


def refresh_data():
    load_companies.clear()


# ----------------------------------------------------------------------------
# HEADER & GLOBAL KPI METRICS
# ----------------------------------------------------------------------------
st.title("A Ray of Hope Foundation - CSR Corporate Outreach Portal")
st.markdown(
    "Track, manage, and grow corporate partnerships across Pune to fund "
    "education programs for underprivileged children. Use the directory below to explore leads, "
    "generate tailored pitches, and analyze outreach campaign performance."
)

df = load_companies()

total_leads = len(df)
total_contacted = df["status"].isin(CONTACTED_STATUSES).sum() if not df.empty else 0
active_discussions = df["status"].isin(DISCUSSION_STATUSES).sum() if not df.empty else 0
pitch_or_funded = df["status"].isin(PITCH_OR_FUNDED_STATUSES).sum() if not df.empty else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Leads in Pune", total_leads)
kpi2.metric("Total Contacted", int(total_contacted))
kpi3.metric("Active Discussions", int(active_discussions))
kpi4.metric("Pitch Sent / Funded", int(pitch_or_funded))

st.divider()

# ----------------------------------------------------------------------------
# MAIN NAVIGATION TABS
# ----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📋 Lead Directory & Tracker", "✉️ Custom Pitch Generator", "📊 Visual Analytics"])


# ============================================================================
# TAB 1: LEAD DIRECTORY & TRACKER
# ============================================================================
with tab1:
    col_filter, col_main = st.columns([1, 3])

    # Sidebar / Left-column Filters
    with col_filter:
        st.subheader("🔍 Filter Leads")
        selected_zone = st.selectbox("Pune Corporate Zone", ZONES, index=0)

        csr_focus_options = ["All"]
        if not df.empty and "csr_focus" in df.columns:
            csr_focus_options += sorted(df["csr_focus"].dropna().unique().tolist())
        selected_focus = st.selectbox("CSR Focus Domain", csr_focus_options, index=0)

        status_options = ["All"] + STATUSES
        selected_status = st.selectbox("Status", status_options, index=0)

        search_term = st.text_input("Search Company / Contact")

        st.markdown("---")
        if st.button("🔄 Refresh Data", use_container_width=True):
            refresh_data()
            st.rerun()

    # Apply Filters
    filtered_df = df.copy()
    if not filtered_df.empty:
        if selected_zone != "All":
            filtered_df = filtered_df[filtered_df["zone"] == selected_zone]

        if selected_focus != "All":
            filtered_df = filtered_df[filtered_df["csr_focus"] == selected_focus]

        if selected_status != "All":
            filtered_df = filtered_df[filtered_df["status"] == selected_status]

        if search_term:
            term = search_term.strip().lower()
            filtered_df = filtered_df[
                filtered_df["company_name"].str.lower().str.contains(term, na=False)
                | filtered_df["contact_person"].str.lower().str.contains(term, na=False)
            ]

    # Data Table & Lead Management
    with col_main:
        st.subheader("📋 Corporate Leads")

        if filtered_df.empty:
            st.info("No leads match the current filters.")
        else:
            display_cols = ["id", "company_name", "zone", "csr_focus", "status", "contact_person"]
            st.dataframe(
                filtered_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            id_to_name = dict(zip(filtered_df["id"], filtered_df["company_name"]))
            c_view, c_update = st.columns(2)

            with c_view:
                st.markdown("**View Lead Details**")
                selected_id_view = st.selectbox(
                    "Select Company",
                    options=list(id_to_name.keys()),
                    format_func=lambda x: f"{x} - {id_to_name[x]}",
                    key="view_select",
                )
                if selected_id_view is not None:
                    row = filtered_df[filtered_df["id"] == selected_id_view].iloc[0]
                    st.write(f"**Contact Person:** {row.get('contact_person', '')} ({row.get('designation', '')})")
                    st.write(f"**Email:** {row.get('email', '')}")
                    linkedin_val = row.get("linkedin_url") or row.get("linkedin")
                    if linkedin_val:
                        st.write(f"**LinkedIn:** [{linkedin_val}]({linkedin_val})")
                    notes_val = row.get("last_notes") or row.get("notes")
                    if notes_val:
                        st.write(f"**Notes:** {notes_val}")

            with c_update:
                st.markdown("**Update Lead Status**")
                if selected_id_view is not None:
                    current_status = df.loc[df["id"] == selected_id_view, "status"].values[0]
                    with st.form("update_lead_form"):
                        new_status = st.selectbox(
                            "New Status",
                            options=STATUSES,
                            index=STATUSES.index(current_status) if current_status in STATUSES else 0,
                        )
                        update_notes = st.text_area("Quick Notes", placeholder="Add progress notes...")
                        if st.form_submit_button("💾 Save Update"):
                            try:
                                update_company_status(selected_id_view, new_status, update_notes)
                                st.success(f"Updated status to '{new_status}'!")
                                refresh_data()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update lead: {e}")

    st.divider()

    # Expander: Add New Lead
    with st.expander("➕ Add New Corporate Lead"):
        with st.form("add_lead_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Company Name *")
                new_zone = st.selectbox("Pune Corporate Zone *", ZONES[1:])
                new_csr_focus = st.text_input("CSR Focus Domain *", placeholder="e.g. Education, Skilling")
                new_contact_person = st.text_input("Contact Person *")
                new_designation = st.text_input("Designation")
            with col2:
                new_email = st.text_input("Email")
                new_linkedin = st.text_input("LinkedIn Profile URL")
                new_status = st.selectbox("Initial Status", STATUSES, index=0)
                new_notes = st.text_area("Notes")

            if st.form_submit_button("✅ Add Lead"):
                if not new_name or not new_contact_person or not new_csr_focus:
                    st.warning("Please fill in all required fields (marked with *).")
                else:
                    try:
                        add_company(
                            new_name,
                            new_zone,
                            new_csr_focus,
                            new_contact_person,
                            new_designation,
                            new_email,
                            new_linkedin,
                            new_status,
                            new_notes,
                        )
                        st.success(f"'{new_name}' added successfully!")
                        refresh_data()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add lead: {e}")


# ============================================================================
# TAB 2: CUSTOM PITCH GENERATOR
# ============================================================================
def generate_pitch_email(company_name, contact_person, csr_focus, email):
    """Generates a tailored CSR pitch email for A Ray of Hope Foundation."""
    subject = f"Partnership Proposal: {company_name} x A Ray of Hope Foundation - CSR in Pune Education"

    body = f"""Dear {contact_person},

I hope this note finds you well. My name is [Your Name], and I represent A Ray of Hope Foundation, a Pune-based NGO dedicated to providing quality primary education, nutrition, and holistic development support to underprivileged children across the city.

We noticed that {company_name}'s CSR initiatives around {csr_focus} align closely with our mission. Over the past few years, our education centers have supported hundreds of children from low-income communities in Pune with structured learning, remedial classes, and access to basic school resources - helping bridge critical learning gaps that would otherwise go unaddressed.

We would be honored to explore a CSR partnership with {company_name} to help us:
  - Expand our primary education centers to reach more children in underserved Pune neighborhoods
  - Provide learning materials, trained educators, and digital literacy tools
  - Track and report measurable impact aligned with your CSR/ESG goals under Section 135 of the Companies Act

We would love the opportunity to share our detailed impact report and a tailored partnership proposal at your convenience. Would you be available for a brief 20-minute call this week or next?

Thank you for considering this partnership. We look forward to the possibility of creating meaningful change together for Pune's children.

Warm regards,
[Your Name]
A Ray of Hope Foundation, Pune
[Your Contact Number] | [Your Email]
"""
    return subject, body


with tab2:
    st.subheader("Custom CSR Pitch Generator")

    if df.empty:
        st.info("No corporate leads available.")
    else:
        company_list = df["company_name"].tolist()
        selected_company = st.selectbox("Select a company", company_list)

        row = df[df["company_name"] == selected_company].iloc[0]
        contact_person = row.get("contact_person", "Sir/Madam")
        csr_focus = row.get("csr_focus", "community development")
        recipient_email = row.get("email", "")

        subject, body = generate_pitch_email(
            selected_company, contact_person, csr_focus, recipient_email
        )

        c_left, c_right = st.columns([2, 1])

        with c_left:
            st.markdown("**Live Preview**")
            st.text_input("To", value=recipient_email, disabled=True)
            st.text_input("Subject", value=subject, disabled=True)
            st.text_area("Body", value=body, height=380)

        with c_right:
            st.markdown("### 🚀 Dispatch Pitch")
            st.write("Clicking below will open your local email client with pre-filled details:")

            # Build mailto link
            mailto_link = (
                f"mailto:{urllib.parse.quote(recipient_email)}"
                f"?subject={urllib.parse.quote(subject)}"
                f"&body={urllib.parse.quote(body)}"
            )

            st.link_button("Open in Mail Client", mailto_link, use_container_width=True)

            st.divider()
            if st.button("Mark as 'Pitch Sent'", use_container_width=True):
                try:
                    update_company_status(row["id"], "Pitch Sent", "Pitch email generated & sent via mail client.")
                    st.success(f"Status updated to 'Pitch Sent' for {selected_company}!")
                    refresh_data()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update status: {e}")


# ============================================================================
# TAB 3: VISUAL ANALYTICS DASHBOARD
# ============================================================================
with tab3:
    st.subheader("Lead Analytics")

    if df.empty:
        st.info("No data available for analytics.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Leads by Pune Zone**")
            zone_counts = df["zone"].value_counts().reset_index()
            zone_counts.columns = ["zone", "count"]

            fig_zone = px.bar(
                zone_counts,
                x="zone",
                y="count",
                color="zone",
                text="count",
                labels={"zone": "Zone", "count": "Number of Leads"},
            )
            fig_zone.update_layout(showlegend=False)
            st.plotly_chart(fig_zone, use_container_width=True)

        with col2:
            st.markdown("**Lead Status Distribution**")
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]

            fig_status = px.pie(
                status_counts,
                names="status",
                values="count",
                hole=0.4,
            )
            st.plotly_chart(fig_status, use_container_width=True)

        st.markdown("---")
        st.markdown("**Quick Stats**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Leads", len(df))
        m2.metric("Pitches Sent", int((df["status"] == "Pitch Sent").sum()))
        m3.metric("New Leads", int((df["status"] == "New Lead").sum()))