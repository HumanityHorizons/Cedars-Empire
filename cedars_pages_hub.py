"""CEDARS EMPIRE 53-page navigation hub for the existing Streamlit application."""
from __future__ import annotations

import streamlit as st

CATALOG = {
    "01 · Member Portal": [
        ("01 Dashboard", "Member overview and account status", "Dashboard"),
        ("02 Wealth Overview", "Wealth and package summary", "Dashboard"),
        ("03 Wallet", "Wallet and ledger view", "My Work & Wallet"),
        ("04 Transfers", "Transfer workflow", "My Work & Wallet"),
        ("05 Deposit Packages", "Deposit package information", "Deposit & Packages"),
        ("06 Deposit Instructions", "Network and destination instructions", "Deposit & Packages"),
        ("07 Deposit History", "Deposit evidence and reconciliation history", "Deposit & Packages"),
        ("08 Withdrawals", "Withdrawal request and approval status", "Withdrawals & Full KYC"),
        ("09 Full KYC", "Identity verification checklist", "Withdrawals & Full KYC"),
        ("10 Staking & Compounding", "Staking status and risk disclosures", "Staking & Compounding"),
        ("11 Earnings", "Evidence-backed earnings records", "Earnings & Wallet"),
        ("12 Contracts", "Member contract records", "Work & Contracts"),
        ("13 My Work", "Assigned work and delivery evidence", "My Work & Wallet"),
        ("14 My Tasks", "Task list and completion evidence", "My Tasks"),
        ("15 Referrals", "Referral links and referral records", "Referral Program"),
        ("16 Reports", "Member report summaries", "Business Reports"),
        ("17 Notifications", "Account notification preferences", "Dashboard"),
        ("18 Support", "Support requests and help", "Dashboard"),
        ("19 Live Studio", "Meeting and session access", "Live Studio"),
        ("20 Calendar & Events", "Scheduled events and reminders", "Calendar & Events"),
    ],
    "02 · Business Operations": [
        ("21 Customer & Clients", "Client profile and relationship management", "Customer & Client Management"),
        ("22 Client Services", "Service delivery records", "Client Services & Contracts"),
        ("23 Work & Contracts", "Contract scopes, dates and deliverables", "Work & Contracts"),
        ("24 Business Pipeline", "Buyer qualification and opportunity stages", "World Grid Marketplace"),
        ("25 World Grid Marketplace", "Provider and buyer marketplace", "World Grid Marketplace"),
        ("26 Cleaning Grid", "Cleaning and property service operations", "Cleaning Grid"),
        ("27 Shelter Grid", "Shelter and accommodation services", "Shelter & Accommodation Grid"),
        ("28 Energy Grid", "Energy and utilities services", "Energy & Utilities Grid"),
        ("29 Solar Energy", "Solar assessment and qualified service referrals", "Energy & Utilities Grid"),
        ("30 Mobility Grid", "Mobility and logistics services", "World Grid Marketplace"),
        ("31 Agriculture Grid", "Agriculture service operations", "World Grid Marketplace"),
        ("32 Data Operations", "Data and AI service delivery", "AI Training & Data Operations"),
        ("33 Robot Operations Dashboard", "Robot fleet, grid readiness, task workflow, evidence gates and system checks (simulation until hardware is verified)", "Robot Operations Dashboard"),
        ("34 Enterprise Grid", "Enterprise service operations", "World Grid Marketplace"),
        ("35 Secure Grid", "Security and compliance service records", "World Grid Marketplace"),
        ("36 Health Grid", "Non-clinical health and wellbeing services", "World Grid Marketplace"),
        ("37 Education Grid", "Education and training services", "World Grid Marketplace"),
        ("38 Connect Grid", "Connectivity and digital service operations", "World Grid Marketplace"),
        ("39 Business Reports", "Business performance and evidence reports", "Business Reports"),
        ("40 AI Scenario Lab", "Business scenario analysis and assumptions", "Business Reports"),
    ],
    "03 · Administrator": [
        ("41 Command Center", "Executive operations and risk overview", "Executive Command Center"),
        ("42 Real Money Engines", "Revenue evidence and delivery controls", "Real Money Engines"),
        ("43 Treasury Management", "Treasury ledger and reconciliation controls", "Treasury Management"),
        ("44 Payments & Treasury", "Payment operations and controls", "Payments & Treasury"),
        ("45 Blockchain Treasury", "Read-only chain evidence and reconciliation", "Blockchain & Treasury"),
        ("46 Payment Operations", "Payment exception and reconciliation review", "Payment Operations"),
        ("47 Daily Crediting", "Evidence-backed activity credit review", "Daily Crediting"),
        ("48 Reports & Referrals", "Referral and reporting administration", "Reports & Referrals"),
        ("49 AI Operations", "AI operations and service health", "AI Operations"),
        ("50 KYC Review", "Restricted identity-review workflow", "Withdrawals & Full KYC"),
        ("51 Branding Settings", "Company branding and assets", "Branding Settings"),
        ("52 Admin Console", "Administrator configuration and access", "Admin Console"),
        ("53 Audit Evidence", "Audit events and supporting evidence", "Executive Command Center"),
    ],
}

def render_cedars_pages_hub(menu_groups: dict[str, list[str]], is_admin: bool) -> None:
    """Render an ordered catalog and route users through the host app's navigation."""
    st.markdown("""
    <style>
    .ce-hub-hero { padding:22px 24px; border-radius:16px; color:#fff;
      background:radial-gradient(circle at 90% 0%,rgba(71,211,218,.28),transparent 32%),
      linear-gradient(115deg,#071a33,#0a3453 65%,#146a70);
      border-bottom:3px solid #d6a84f; margin-bottom:16px; }
    .ce-hub-hero h2 { color:#fff !important; margin:0; font-size:27px; }
    .ce-hub-hero p { color:#e0edf6 !important; margin:6px 0 0; }
    [data-testid="stExpander"] { border:1px solid #d5e0ea; border-radius:12px;
      background:linear-gradient(145deg,#fff,#f3f8fc); margin-bottom:10px; }
    [data-testid="stExpander"] summary { font-weight:800; color:#0a2342; }
    .ce-hub-chip { display:inline-block; padding:4px 8px; border-radius:20px;
      background:#e8f4f5; color:#0a4954; font-size:11px; font-weight:700; }
    </style>
    <div class="ce-hub-hero">
      <h2>CEDARS EMPIRE · BUSINESS & AI COMMAND HUB</h2>
      <p>53-page directory · Member services · Business grids · Robotics · Admin controls</p>
    </div>
    """, unsafe_allow_html=True)
    st.header("Complete 53-page directory")
    st.caption("One navigation hub for the member portal, business operations, and administrator workspace.")
    st.info("UI ASSEMBLED · VERIFICATION PENDING. This directory brings all 53 page entries into one website. Verify each page in its deployed workflow; a catalog entry is not proof that its business process, payment rail, persistence, or external integration is operational.")
    st.warning("Status legend: UI ASSEMBLED = page is listed in the website hub; ROUTE MAPPED = an existing application destination was found; VERIFICATION PENDING = deployment/runtime and workflow checks remain outstanding. No page is marked production-verified by this directory.")

    # Keep all 53 catalog entries visible to make the complete site auditable.
    # Authorization is enforced below: member accounts can view locked admin
    # entries in the directory but cannot open administrator workflows.
    visible = dict(CATALOG)

    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        section = st.selectbox("Section", list(visible), key="cedars53_section")
        items = visible[section]
        selected_title = st.selectbox("Page", [item[0] for item in items], key="cedars53_page")
        selected = next(item for item in items if item[0] == selected_title)
        st.caption(f"{len(items)} pages in this section · 53 pages in the full catalog")
        query = st.text_input("Search all pages", placeholder="Search by page name or function", key="cedars53_search")
        if query.strip():
            results = [(group, item) for group, group_items in visible.items() for item in group_items
                       if query.casefold() in " ".join(item).casefold()]
            st.markdown("**Search results**")
            for group, item in results:
                st.write(f"{item[0]} — {group} · UI assembled · verification pending")

    with col2:
        st.subheader(selected[0])
        st.write(selected[1])
        target = selected[2]
        st.markdown(f"**Existing application destination:** {target}")
        st.warning("PAGE STATUS: UI ASSEMBLED · VERIFICATION PENDING")
        st.caption("Verify on deployment: page loads, correct role/access, save and reload, persistence after restart, and relevant workflow-specific behavior. For money-related pages, independently verify settlement before treating funds as real or available.")
        if section == "03 · Administrator" and not is_admin:
            st.error("LOCKED · Administrator access required. This page is listed for completeness but cannot be opened by a member account.")
        elif target in {"Executive Command Center", "Treasury Management", "Real Money Engines",
                        "Payments & Treasury", "Blockchain & Treasury", "Payment Operations",
                        "Daily Crediting", "Reports & Referrals", "AI Operations", "Branding Settings",
                        "Admin Console", "Business Opportunity Pipeline"} and not is_admin:
            st.error("LOCKED · This destination is administrator-only.")
        else:
            group_match = next((group for group, pages in menu_groups.items() if target in pages), None)
            if group_match and st.button("Open existing workflow", type="primary", key="cedars53_open"):
                st.session_state["ce_pending_top_menu"] = group_match
                st.session_state["ce_pending_sub_menu"] = target
                st.rerun()
            elif not group_match:
                st.warning("No exact existing navigation handler was found for this entry. It needs an explicit route before production release.")
        st.caption("No new account store is created. Existing app authentication, database, and role checks remain the source of truth.")

    st.divider()
    st.markdown("""
    <div class="ce-hub-hero" style="background:radial-gradient(circle at 90% 0%,rgba(214,168,79,.24),transparent 32%),linear-gradient(115deg,#071a33,#103c5a 65%,#145c63)">
      <h2>🤖 Robot Simulation · Landing Page</h2>
      <p>Explore the robot fleet concept, business grids, task-evidence gates, commercial readiness, and system checks.</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("SIMULATION ONLY · NO PHYSICAL ROBOTS CONNECTED. Worker targets and catalogue entries are planning information, not live workers, completed jobs, or earned revenue.")
    robot_target = "Robot Operations Dashboard"
    robot_group = next((group for group, pages in menu_groups.items() if robot_target in pages), None)
    if robot_group:
        if st.button("Open Robot Simulation Dashboard →", type="primary", key="cedars_robot_landing_open"):
            st.session_state["ce_pending_top_menu"] = robot_group
            st.session_state["ce_pending_sub_menu"] = robot_target
            st.rerun()
    else:
        st.warning("Robot dashboard is not present in this account's navigation. The simulation landing information is shown here, but the dashboard route needs to be enabled for this role.")

    st.divider()
    st.subheader("All 53 pages · visible directory")
    st.caption("All 53 catalog entries are displayed below as cards. Administrator pages remain locked for member accounts. Each route must still be tested in the deployed app.")
    flat_items = [(group, item) for group, group_items in visible.items() for item in group_items]
    page_cols = st.columns(3, gap="medium")
    for index, (group, item) in enumerate(flat_items):
        title, description, target = item
        with page_cols[index % 3]:
            is_admin_entry = group == "03 · Administrator"
            target_group = next((name for name, pages in menu_groups.items() if target in pages), None)
            locked = is_admin_entry and not is_admin
            st.markdown(
                f'<div class="ce-grid-card" style="min-height:140px;margin-bottom:8px">'
                f'<div class="ce-grid-number">{group} · PAGE {index + 1:02d}</div>'
                f'<div class="ce-grid-title">{title}</div>'
                f'<div class="ce-grid-copy">{description}</div>'
                f'<div style="margin-top:9px"><span class="ce-hub-chip">{"LOCKED · ADMIN ONLY" if locked else "VERIFICATION PENDING"}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if locked:
                st.button("Restricted to administrators", key=f"cedars53_card_{index}", disabled=True, use_container_width=True)
            elif target_group:
                if st.button("Open page →", key=f"cedars53_card_{index}", use_container_width=True):
                    st.session_state["ce_pending_top_menu"] = target_group
                    st.session_state["ce_pending_sub_menu"] = target
                    st.rerun()
            else:
                st.button("Route not enabled", key=f"cedars53_card_{index}", disabled=True, use_container_width=True)
    st.caption("Integrity note: estimates, draft records, and unverified transaction claims must not be presented as confirmed revenue or available funds.")
