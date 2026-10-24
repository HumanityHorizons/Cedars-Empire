"""Unified CEDARS EMPIRE AI workforce, grid and package dashboard.

Shows the long-term worker target and configured catalogues without fabricating
active workers, customer orders, revenue, or payment confirmations.
"""
from __future__ import annotations

import streamlit as st
from hh_grid_marketplace import GRID_CATALOG
from hh_robotics import robot_grid_catalog

WORKER_TARGET = 25_000_000
PACKAGES = [
    {"name": "Cedars Seed", "amount": 300, "purpose": "Entry services, basic dashboard and training"},
    {"name": "Cedars Root", "amount": 1_000, "purpose": "Expanded services, reporting and business planning"},
    {"name": "Cedars Branch", "amount": 2_500, "purpose": "Advanced analytics, mentorship and eligible opportunities"},
    {"name": "Cedars Grove", "amount": 5_000, "purpose": "Business acceleration and advanced reporting"},
    {"name": "Cedars Forest", "amount": 10_000, "purpose": "Advanced services, reporting and eligible leadership programs"},
    {"name": "Cedars Empire", "amount": 25_000, "purpose": "Premium services and eligible executive programs"},
]

STATUS = {
    "standby": ("🟠", "STANDBY"),
    "registered": ("🔵", "REGISTERED"),
    "connected": ("🟢", "CONNECTED — VERIFY INTEGRATION"),
    "maintenance": ("🟡", "MAINTENANCE"),
    "blocked": ("🔴", "BLOCKED"),
}


def render_robot_dashboard() -> None:
    """Render the unified AI worker, grid, package and money-control overview."""
    st.markdown("""
    <style>
    .ce-unify-hero{background:linear-gradient(120deg,#071D33,#123D60 68%,#1B5B66);
      border:1px solid #244E68;border-bottom:4px solid #D6A84F;border-radius:16px;
      padding:24px;margin-bottom:18px;color:#fff}
    .ce-unify-hero h1{color:#fff!important;margin:0;font-size:29px}
    .ce-unify-hero p{color:#DCEAF3!important;margin:8px 0 0}
    .ce-unify-card{background:var(--secondary-background-color);border:1px solid rgba(128,128,128,.28);
      border-top:3px solid #D6A84F;border-radius:12px;padding:14px;min-height:112px;margin-bottom:8px}
    .ce-unify-name{font-size:16px;font-weight:800}
    .ce-unify-meta{font-size:12px;opacity:.78;margin-top:7px}
    </style>
    <div class="ce-unify-hero">
      <div style="font-size:11px;letter-spacing:2px;font-weight:800;color:#E7C77D">CEDARS EMPIRE · UNIFIED OPERATIONS</div>
      <h1>AI Workforce, Grids & Packages</h1>
      <p>One operating view for worker readiness, real-work grids, customer packages and evidence-backed money flows.</p>
    </div>
    """, unsafe_allow_html=True)

    robots = robot_grid_catalog()
    connected = sum(1 for item in robots if item.get("status") == "connected")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Long-term AI worker target", f"{WORKER_TARGET:,}")
    c2.metric("Configured grid catalogue", len(GRID_CATALOG))
    c3.metric("Robot grid entries", len(robots))
    c4.metric("Connected robot grids", connected)
    st.caption("VISUAL SIMULATION ONLY · NO HARDWARE CONNECTED — runtime connection must be independently verified.")
    st.caption(
        "The 25,000,000 figure is a long-term target, not the number of deployed workers. "
        "These counts describe configured catalogue entries, not active hardware or verified revenue."
    )

    st.subheader("1 · AI worker fleet")
    st.write(
        "Workers should be registered with a unique identity, capability, assigned grid, "
        "permission scope, task history, cost limit and health state. A worker counts as active "
        "only after a real runtime heartbeat is integrated and verified."
    )
    worker_cols = st.columns(3)
    worker_cols[0].metric("Runtime-connected workers", "Not connected")
    worker_cols[1].metric("Persisted task queue", "Not verified")
    worker_cols[2].metric("Verified task completions", "Not connected")
    st.info(
        "Activation gate: verify worker runtime, safe permissions, durable task storage, "
        "completion evidence and cost controls before reporting operational worker counts."
    )

    st.subheader("2 · Business grid catalogue")
    query = st.text_input("Find a grid or service", placeholder="Search energy, data, mobility…", key="ce_unified_grid_search")
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
                    st.markdown('<div class="ce-unify-card">', unsafe_allow_html=True)
                    st.markdown(f"**{item.get('name', 'Unnamed grid')}**")
                    st.caption(str(item.get("sector", "Sector not specified")))
                    tasks = item.get("tasks", [])
                    st.write(", ".join(tasks[:3]) if tasks else "Service definition pending")
                    st.caption("Proof: " + str(item.get("proof", "Evidence requirements pending")))
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No grids match that search.")
    st.caption(
        "A listed grid is a business-service definition, not proof of a connected robot, "
        "available supplier, paying customer or completed transaction."
    )

    st.subheader("3 · Cedars Growth Ladder packages")
    st.write(
        "Packages define customer services and entitlements. A package purchase is not "
        "automatically profit, staking yield or a guaranteed earning."
    )
    package_cols = st.columns(3)
    for index, package in enumerate(PACKAGES):
        with package_cols[index % 3]:
            st.markdown('<div class="ce-unify-card">', unsafe_allow_html=True)
            st.markdown(f"**{package['name']}**")
            st.markdown(f"### ${package['amount']:,} USD")
            st.write(package["purpose"])
            st.caption("Contract terms, eligibility and refund obligations must be confirmed.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("4 · How work becomes real money")
    stages = [
        ("01 · Customer order", "A real buyer, agreed scope, price and payment terms."),
        ("02 · Worker assignment", "Permission-checked worker and grid assignment within a cost limit."),
        ("03 · Delivery evidence", "Saved work product, task ID and customer acceptance."),
        ("04 · Invoice and payment", "Invoice linked to the task; payment independently checked."),
        ("05 · Reconciliation", "Fees, costs, refunds and customer obligations accounted for."),
        ("06 · Sustainable reinvestment", "Use only available, reconciled funds under approved budgets."),
    ]
    for title, description in stages:
        st.markdown(f"**{title}** — {description}")
    st.warning(
        "Financial integrity: leads, forecasts, package balances, unconfirmed transfers and "
        "self-entered statuses must not be counted as verified revenue. Never credit the same "
        "task or transaction twice."
    )

    st.subheader("5 · Readiness gates")
    st.dataframe([
        {"Gate": "Worker runtime and identity", "Status": "Not verified"},
        {"Gate": "Grid provider and customer evidence", "Status": "Must be verified per service"},
        {"Gate": "Package contracts and entitlements", "Status": "Requires contract validation"},
        {"Gate": "PostgreSQL persistence across refresh/restart", "Status": "Must be tested"},
        {"Gate": "Authentication and role boundaries", "Status": "Must be tested"},
        {"Gate": "Independent payment verification and reconciliation", "Status": "Must be tested"},
        {"Gate": "One end-to-end paid commercial task", "Status": "Not yet evidenced here"},
    ], use_container_width=True, hide_index=True)
