"""Clean robotic AI dashboard for CEDARS EMPIRE.

Configured catalogue data and planning targets only; no fabricated live counts.
"""
from __future__ import annotations

import streamlit as st
from hh_grid_marketplace import GRID_CATALOG
from hh_robotics import robot_grid_catalog

WORKER_TARGET = 250_000_000
PACKAGES = [
    {"name": "Cedars Seed", "amount": 300},
    {"name": "Cedars Root", "amount": 1_000},
    {"name": "Cedars Branch", "amount": 2_500},
    {"name": "Cedars Grove", "amount": 5_000},
    {"name": "Cedars Forest", "amount": 10_000},
    {"name": "Cedars Empire", "amount": 25_000},
]


def render_robot_dashboard() -> None:
    """Render a concise, form-oriented robotic operations dashboard."""
    st.markdown("""
    <style>
    .ce-robot-hero{background:linear-gradient(115deg,#071d33,#123d60);
      border-bottom:3px solid #d6a84f;border-radius:10px;padding:18px 22px;
      color:#fff;margin-bottom:14px}
    .ce-robot-hero h2{color:#fff!important;margin:0;font-size:25px}
    .ce-robot-hero p{color:#dceaf3!important;margin:5px 0 0;font-size:12px}
    div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.25);
      border-radius:8px;padding:12px}
    </style>
    <div class="ce-robot-hero">
      <h2>CEDARS EMPIRE · ROBOTIC AI DASHBOARD</h2>
      <p>WORKFORCE · GRIDS · TASKS · PACKAGES · TREASURY</p>
    </div>
    """, unsafe_allow_html=True)

    robots = robot_grid_catalog()
    configured = len(GRID_CATALOG)
    robot_entries = len(robots)
    connected_entries = sum(1 for item in robots if item.get("status") == "connected")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI WORKER TARGET", f"{WORKER_TARGET:,}")
    m2.metric("BUSINESS GRIDS", configured)
    m3.metric("ROBOT GRID TYPES", robot_entries)
    m4.metric("CONNECTED GRID ENTRIES", connected_entries)

    st.caption("VISUAL SIMULATION ONLY · NO HARDWARE CONNECTED")
    st.caption("The 250,000,000 figure is a long-term target, not the number of deployed workers. Catalogue counts are not live worker counts or revenue.")

    fleet_tab, grids_tab, packages_tab, money_tab, checks_tab = st.tabs(
        ["ROBOT FLEET", "BUSINESS GRIDS", "PACKAGES", "REAL MONEY FLOW", "SYSTEM CHECKS"]
    )

    with fleet_tab:
        a, b, c = st.columns(3)
        a.metric("LIVE WORKERS", "Not connected")
        b.metric("TASK QUEUE", "Not verified")
        c.metric("VERIFIED TASKS", "Not connected")
        st.dataframe([
            {"CONTROL": "Worker identity", "STATUS": "Not verified"},
            {"CONTROL": "Runtime heartbeat", "STATUS": "Not connected"},
            {"CONTROL": "Task evidence storage", "STATUS": "Not verified"},
            {"CONTROL": "Permission and cost limits", "STATUS": "Required"},
        ], use_container_width=True, hide_index=True)

    with grids_tab:
        query = st.text_input("SEARCH GRIDS", placeholder="Grid name or service", key="ce_unified_grid_search")
        filtered = [
            item for item in GRID_CATALOG
            if not query.strip() or query.lower() in (
                str(item.get("name", "")) + " " + str(item.get("sector", "")) + " "
                + " ".join(item.get("tasks", []))
            ).lower()
        ]
        if filtered:
            for start in range(0, len(filtered), 3):
                cols = st.columns(3)
                for col, item in zip(cols, filtered[start:start + 3]):
                    with col:
                        st.markdown(f"**{item.get('name', 'Unnamed grid')}**")
                        st.caption(str(item.get("sector", "—")))
                        tasks = item.get("tasks", [])
                        st.write(", ".join(tasks[:2]) if tasks else "Service pending")
                        st.button("OPEN GRID", key="ce_grid_" + str(item.get("name", start)), use_container_width=True, disabled=True)
        else:
            st.info("No matching grids.")

    with packages_tab:
        cols = st.columns(3)
        for i, package in enumerate(PACKAGES):
            with cols[i % 3]:
                st.markdown(f"**{package['name'].upper()}**")
                st.subheader(f"${package['amount']:,} USD")
                st.button("VIEW PACKAGE", key=f"ce_package_{i}", use_container_width=True, disabled=True)
        st.caption("Package price is not revenue, profit or a guaranteed return.")

    with money_tab:
        st.dataframe([
            {"STAGE": "01 · Customer order", "STATUS": "Required"},
            {"STAGE": "02 · Worker assignment", "STATUS": "Not verified"},
            {"STAGE": "03 · Delivery evidence", "STATUS": "Not verified"},
            {"STAGE": "04 · Payment verification", "STATUS": "Not connected"},
            {"STAGE": "05 · Reconciliation", "STATUS": "Not connected"},
            {"STAGE": "06 · Net revenue", "STATUS": "Not available"},
        ], use_container_width=True, hide_index=True)
        st.warning("Only independently verified, reconciled receipts count as revenue. Never count leads, forecasts or unconfirmed transfers.")

    with checks_tab:
        st.dataframe([
            {"SYSTEM": "Authentication and roles", "STATUS": "Must be tested"},
            {"SYSTEM": "PostgreSQL persistence", "STATUS": "Must be tested"},
            {"SYSTEM": "Worker runtime", "STATUS": "Not connected"},
            {"SYSTEM": "Grid customer evidence", "STATUS": "Must be verified"},
            {"SYSTEM": "Payment reconciliation", "STATUS": "Must be tested"},
            {"SYSTEM": "End-to-end paid task", "STATUS": "Not evidenced"},
        ], use_container_width=True, hide_index=True)
