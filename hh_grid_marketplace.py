"""CEDARS EMPIRE global real-work grid registry and marketplace UI.

This module deliberately does not simulate robot telemetry, revenue, payments, or earnings.
Connectors and durable persistence must be configured and verified before live operation.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

GRID_CATALOG = [
    {
        "id": "shelter",
        "name": "Shelter Grid",
        "sector": "Physical services",
        "tasks": ["Bed-night", "Room / apartment", "Emergency shelter"],
        "unit": "completed service",
        "proof": "Provider record and recipient/client confirmation",
        "equipment": "Verified accommodation provider; optional occupancy sensors",
    },
    {
        "id": "energy",
        "name": "Energy Grid",
        "sector": "Energy",
        "tasks": ["Solar generation inspection", "Battery charge service", "Cooking gas / hot water", "Lighting service", "Energy-meter reading"],
        "unit": "verified service or measured kWh",
        "proof": "Meter / inverter evidence, service record, client acceptance",
        "equipment": "Solar / battery telemetry, compatible inspection or cleaning robot where available",
    },
    {
        "id": "cleaning",
        "name": "Cleaning Grid",
        "sector": "Physical services",
        "tasks": ["Home cleaning", "Laundry", "Compound cleaning", "Solar-panel cleaning"],
        "unit": "accepted job",
        "proof": "Work order, before/after evidence where appropriate, client acceptance",
        "equipment": "Verified operator and/or compatible cleaning robot",
    },
    {
        "id": "data",
        "name": "Data & AI Grid",
        "sector": "Digital work",
        "tasks": ["Survey", "AI data labeling", "Market-price collection", "Image annotation", "AI evaluation", "Robot-vision review"],
        "unit": "accepted item or task batch",
        "proof": "Quality score, reviewer approval, source and task identifiers",
        "equipment": "Authorized software/API and human quality review",
    },
    {
        "id": "mobility",
        "name": "Mobility Grid",
        "sector": "Transport & logistics",
        "tasks": ["Taxi / ride", "Shared mobility", "Delivery", "Luggage movement", "Warehouse picking / movement", "Inventory scan"],
        "unit": "completed trip, delivery or task",
        "proof": "Order ID, route / delivery confirmation, operator record",
        "equipment": "Verified provider; compatible autonomous mobile robot where legally and operationally supported",
    },
    {
        "id": "food-water",
        "name": "Food & Water Grid",
        "sector": "Food & essential services",
        "tasks": ["Meal service", "Water delivery", "Cooking service", "Garden plot / crop service", "Crop monitoring"],
        "unit": "verified delivery or completed service",
        "proof": "Order, quantity / quality evidence, recipient confirmation",
        "equipment": "Verified supplier; optional agricultural or delivery robotics",
    },
    {
        "id": "care",
        "name": "Care Grid",
        "sector": "Care services",
        "tasks": ["Care-service booking", "Accessible support", "Wellbeing check-in"],
        "unit": "authorized, completed service",
        "proof": "Consent-aware service record and authorized provider confirmation",
        "equipment": "Verified qualified provider; no autonomous high-risk care without appropriate oversight",
    },
    {
        "id": "industrial-robotics",
        "name": "Industrial Robotics Grid",
        "sector": "Robotics",
        "tasks": ["Assembly", "Packaging", "Quality inspection", "Machine tending"],
        "unit": "accepted production task",
        "proof": "Machine telemetry, quality-control result and client acceptance",
        "equipment": "Registered robot, controller/API, safety interlocks and verified operator",
    },
    {
        "id": "warehouse-robotics",
        "name": "Warehouse Robotics Grid",
        "sector": "Robotics",
        "tasks": ["Autonomous mobile robot movement", "Picking support", "Inventory scanning", "Sorting"],
        "unit": "accepted pick, scan or movement",
        "proof": "WMS / task ID, device telemetry and exception record",
        "equipment": "Registered AMR / robot and warehouse system integration",
    },
    {
        "id": "agri-robotics",
        "name": "Agriculture Robotics Grid",
        "sector": "Robotics",
        "tasks": ["Crop scouting", "Precision weeding", "Irrigation inspection", "Harvesting support"],
        "unit": "verified field task",
        "proof": "Geotagged field evidence, task telemetry and operator/client sign-off",
        "equipment": "Compatible field robot or verified agricultural robotics provider",
    },
    {
        "id": "solar-robotics",
        "name": "Solar & Energy Robotics Grid",
        "sector": "Robotics",
        "tasks": ["Panel cleaning", "Thermal inspection", "Fault detection", "Site inspection"],
        "unit": "accepted inspection or service",
        "proof": "Site ID, timestamped inspection evidence, measured result and client acceptance",
        "equipment": "Compatible cleaning/inspection robot, sensor payload and trained operator",
    },
    {
        "id": "robot-vision",
        "name": "Robot Vision & Telemetry Grid",
        "sector": "Robotics and AI",
        "tasks": ["Image / video annotation", "Sensor-data validation", "Visual defect review", "Robot-model evaluation"],
        "unit": "quality-approved data item or batch",
        "proof": "Dataset/task ID, quality checks, reviewer approval and permitted data provenance",
        "equipment": "Authorized camera/sensor feed, dataset access and quality-review workflow",
    },
]

GRID_STATUSES = [
    "Discovery only",
    "Provider verification required",
    "Agreement required",
    "Ready for controlled test",
    "Live — evidence verified",
    "Paused",
]


def render_grid_marketplace() -> None:
    """Render a global grid registry without claiming unverified live activity."""
    st.title("Real Work & Robot Grid Marketplace")
    st.caption("Global registry • evidence-first • no simulated earnings or robot activity")

    summary = pd.DataFrame([
        {"Control": "Grid types", "Status": str(len(GRID_CATALOG))},
        {"Control": "Live providers", "Status": "Not verified by this registry"},
        {"Control": "Verified revenue", "Status": "Read only from reconciled payment records"},
        {"Control": "Robot telemetry", "Status": "Requires a registered device integration"},
    ])
    st.dataframe(summary, hide_index=True, use_container_width=True)

    query = st.text_input("Search grids or tasks", placeholder="e.g. solar inspection, data labeling, delivery")
    sectors = ["All sectors"] + sorted({item["sector"] for item in GRID_CATALOG})
    sector = st.selectbox("Sector", sectors)
    rows = []
    for grid in GRID_CATALOG:
        searchable = " ".join([grid["name"], grid["sector"], *grid["tasks"]]).casefold()
        if query and query.casefold() not in searchable:
            continue
        if sector != "All sectors" and grid["sector"] != sector:
            continue
        rows.append({
            "Grid": grid["name"],
            "Sector": grid["sector"],
            "Available task types": ", ".join(grid["tasks"]),
            "Unit of work": grid["unit"],
            "Status": "Discovery only",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    names = {grid["name"]: grid for grid in GRID_CATALOG}
    selected_name = st.selectbox("Grid details", list(names))
    selected = names[selected_name]
    left, right = st.columns(2)
    with left:
        st.subheader("Task scope")
        st.write(", ".join(selected["tasks"]))
        st.write("**Unit:** " + selected["unit"])
        st.write("**Required evidence:** " + selected["proof"])
    with right:
        st.subheader("Operational requirements")
        st.write(selected["equipment"])
        st.info("No provider, robot, agreement, job completion, or revenue is certified by this listing.")

    with st.expander("Register a provider or robot for review"):
        st.caption("Submitting this form records nothing yet; persistence and verification workflow must be connected before activation.")
        with st.form("grid_provider_review_request"):
            provider_name = st.text_input("Provider / robot owner")
            contact = st.text_input("Business contact")
            device_or_service = st.text_input("Robot model, API, or service offered")
            evidence_url = st.text_input("Evidence / official website URL")
            safety_notes = st.text_area("Safety, operating area and limitations")
            submitted = st.form_submit_button("Prepare review request")
        if submitted:
            if not provider_name.strip() or not device_or_service.strip():
                st.error("Provider name and robot/service details are required.")
            else:
                st.warning("Review request prepared for this session only. It has not been saved, verified, contracted, or activated.")
                st.json({
                    "grid": selected["id"],
                    "provider_name": provider_name.strip(),
                    "contact": contact.strip(),
                    "device_or_service": device_or_service.strip(),
                    "evidence_url": evidence_url.strip(),
                    "safety_notes": safety_notes.strip(),
                    "status": "NOT VERIFIED — not persisted",
                })

    st.caption("Live status requires verified provider identity, a written agreement, task evidence, client acceptance, durable database records and reconciled payment evidence.")
