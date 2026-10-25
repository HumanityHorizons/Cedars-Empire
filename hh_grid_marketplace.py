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


    {
        "id": "security", "name": "SecurityGrid", "sector": "Security & infrastructure",
        "tasks": ["CCTV installation", "AI video analytics", "ANPR", "Access control", "Biometrics", "Visitor management", "Alarm systems", "Incident reporting", "Parking management", "Remote monitoring"],
        "unit": "verified installation or service contract", "proof": "Authorized installation record, customer acceptance, access and privacy controls",
        "equipment": "Verified security integrator, licensed devices and lawful monitoring permissions",
    },
    {
        "id": "workforce", "name": "WorkforceGrid", "sector": "Enterprise operations",
        "tasks": ["Recruitment", "Payroll processing", "Attendance", "Leave management", "Performance management", "Employee self-service", "Learning and certification"],
        "unit": "accepted subscription or processed service", "proof": "Authorized HR records, payroll reconciliation and customer acceptance",
        "equipment": "Role-based HR system; biometric data only with lawful basis and safeguards",
    },
    {
        "id": "finance", "name": "FinanceGrid", "sector": "Enterprise operations",
        "tasks": ["Accounting", "Budgeting", "Procurement", "Expense management", "Audit trail", "Treasury reporting", "Revenue collection", "Financial reports"],
        "unit": "accepted subscription or service", "proof": "Immutable audit references, reconciled source documents and authorized approvals",
        "equipment": "Accounting integrations and restricted financial access",
    },
    {
        "id": "commerce", "name": "CommerceGrid", "sector": "Enterprise operations",
        "tasks": ["Point of sale", "Inventory", "Retail operations", "E-commerce", "Sales management", "Supplier management", "CRM"],
        "unit": "subscription or reconciled order", "proof": "Order ID, invoice, fulfilment record and payment-provider reconciliation",
        "equipment": "POS / commerce platform and verified merchant integrations",
    },
    {
        "id": "connect", "name": "ConnectGrid", "sector": "Digital infrastructure",
        "tasks": ["Fiber networks", "Wireless networks", "Hotspots", "LAN/WAN", "Managed networks", "Data connectivity"],
        "unit": "accepted installation or service period", "proof": "Service-level records, uptime evidence and customer acceptance",
        "equipment": "Authorized network provider and managed network telemetry",
    },
    {
        "id": "cloud", "name": "CloudGrid", "sector": "Digital infrastructure",
        "tasks": ["VPS", "Dedicated hosting", "Domains", "Email hosting", "Backup", "Disaster recovery", "Managed servers"],
        "unit": "paid subscription or measured usage", "proof": "Provider invoice, provisioned resource ID, uptime and billing reconciliation",
        "equipment": "Verified hosting/cloud provider integration",
    },
    {
        "id": "data-platform", "name": "DataGrid", "sector": "Digital infrastructure",
        "tasks": ["Data warehouse", "Business intelligence", "Analytics", "Dashboards", "Data lakes", "AI models"],
        "unit": "accepted analysis or subscription", "proof": "Dataset provenance, permission check, reproducible output and client acceptance",
        "equipment": "Authorized data sources, privacy controls and analytics pipeline",
    },
    {
        "id": "facility", "name": "FacilityGrid", "sector": "Operations",
        "tasks": ["Electrical service", "Plumbing", "Air conditioning", "Building maintenance", "Janitorial services", "Asset maintenance", "Technician dispatch"],
        "unit": "accepted work order", "proof": "Work order, qualified technician record, safety checklist and customer sign-off",
        "equipment": "Verified service provider; compatible inspection robots where available",
    },
    {
        "id": "fleet", "name": "FleetGrid", "sector": "Mobility & logistics",
        "tasks": ["Vehicle tracking", "Fuel monitoring", "Route planning", "Driver management", "Vehicle maintenance", "Fleet analytics"],
        "unit": "vehicle-month or accepted service", "proof": "Vehicle/device IDs, consented telemetry, work order and billing evidence",
        "equipment": "Verified GPS / fleet platform and authorized vehicle devices",
    },
    {
        "id": "logistics", "name": "LogisticsGrid", "sector": "Mobility & logistics",
        "tasks": ["Cargo tracking", "Warehouse management", "Dispatch", "Route optimization", "Import/export tracking"],
        "unit": "accepted shipment or subscription", "proof": "Shipment ID, custody events, delivery proof and client acceptance",
        "equipment": "Carrier / warehouse integration and verified operators",
    },
    {
        "id": "climate", "name": "ClimateGrid", "sector": "Energy, environment & agriculture",
        "tasks": ["Carbon tracking", "Environmental monitoring", "ESG reporting", "Climate risk analytics", "Disaster monitoring"],
        "unit": "accepted report, dataset or subscription", "proof": "Source provenance, measurement method, uncertainty and review record",
        "equipment": "Authorized environmental sensors and documented data sources",
    },
    {
        "id": "agriculture-platform", "name": "AgricultureGrid", "sector": "Energy, environment & agriculture",
        "tasks": ["Farm management", "Livestock tracking", "Irrigation monitoring", "Market linkages", "Climate advisory", "Input planning", "Produce aggregation"],
        "unit": "accepted service, transaction or subscription", "proof": "Farmer/provider consent, quantity/quality records and verified order evidence",
        "equipment": "Farm software, authorized sensors and compatible field robots",
    },
    {
        "id": "city", "name": "CityGrid", "sector": "Public sector",
        "tasks": ["Smart traffic", "Smart parking", "ANPR", "Public safety", "Smart lighting", "Citizen reporting"],
        "unit": "contract milestone or accepted service", "proof": "Public procurement record, lawful data-use basis, security and acceptance evidence",
        "equipment": "Authorized city infrastructure and privacy-impact-reviewed integrations",
    },
    {
        "id": "government", "name": "GovGrid", "sector": "Public sector",
        "tasks": ["E-government", "Licensing workflows", "Tax collection systems", "Citizen services", "Document management"],
        "unit": "accepted contract milestone", "proof": "Procurement authority, signed contract, security review and milestone acceptance",
        "equipment": "Authorized government systems; compliance and access controls",
    },
    {
        "id": "health", "name": "HealthGrid", "sector": "Public services",
        "tasks": ["Hospital management", "Telemedicine", "Pharmacy management", "Patient records", "Medical inventory"],
        "unit": "facility subscription or accepted service", "proof": "Facility authorization, privacy/security controls and clinical governance review",
        "equipment": "Verified health provider and compliant clinical-system integrations",
    },
    {
        "id": "education", "name": "EduGrid", "sector": "Public services",
        "tasks": ["School management", "Learning management", "Examinations", "Attendance", "E-libraries"],
        "unit": "institution/student subscription", "proof": "Institution authorization, access permissions and service acceptance",
        "equipment": "Verified education platform and age-appropriate safeguarding controls",
    },
    {
        "id": "service", "name": "ServiceGrid", "sector": "Marketplaces",
        "tasks": ["Electrician booking", "Plumbing", "Security expertise", "Mechanic booking", "Cleaning", "Job matching"],
        "unit": "accepted job", "proof": "Provider identity/qualification, job scope, customer acceptance and payment reconciliation",
        "equipment": "Verified service providers and marketplace order workflow",
    },
    {
        "id": "contractor", "name": "ContractorGrid", "sector": "Marketplaces",
        "tasks": ["Project management", "Contractor marketplace", "BOQ management", "Asset tracking"],
        "unit": "accepted milestone or subscription", "proof": "Written contract, BOQ version, site evidence and authorized milestone approval",
        "equipment": "Verified contractors and project-management integrations",
    },
    {
        "id": "talent", "name": "TalentGrid", "sector": "Marketplaces",
        "tasks": ["AI experts", "Developers", "Designers", "Consultants", "Trainers", "Freelance delivery"],
        "unit": "accepted deliverable", "proof": "Contract, scoped deliverable, reviewer/client acceptance and payment reference",
        "equipment": "Verified talent profiles and contract workflow",
    },
    {
        "id": "ai-services", "name": "AIGrid", "sector": "AI & robotics",
        "tasks": ["AI agents", "Automation", "Predictive analytics", "Computer vision", "Voice AI"],
        "unit": "accepted task, usage or subscription", "proof": "Run ID, authorized inputs, output checks, cost record and client acceptance",
        "equipment": "Configured model/API integrations with spend limits and privacy controls",
    },
    {
        "id": "robot", "name": "RobotGrid", "sector": "AI & robotics",
        "tasks": ["Security robots", "Agricultural robots", "Educational robots", "Industrial robots", "Robot leasing and maintenance"],
        "unit": "accepted robot task, lease or service", "proof": "Registered device, telemetry/task ID, safety checks, operator sign-off and client acceptance",
        "equipment": "Compatible robot/controller API, safety interlocks and verified operator",
    },
    {
        "id": "knowledge", "name": "KnowledgeGrid", "sector": "Knowledge & media",
        "tasks": ["Courses", "Certifications", "Learning content", "Professional development"],
        "unit": "course enrolment or subscription", "proof": "Course/version ID, completion record and authorized certification evidence",
        "equipment": "Learning platform and verified content/licensing rights",
    },
    {
        "id": "media", "name": "MediaGrid", "sector": "Knowledge & media",
        "tasks": ["Streaming", "Podcasts", "Online radio", "Digital advertising", "Content distribution"],
        "unit": "verified campaign, subscription or distribution service", "proof": "Content rights, campaign delivery metrics and reconciled invoice/payment",
        "equipment": "Authorized streaming/media hosting and advertising integrations",
    },
    {
        "id": "community", "name": "CommunityGrid", "sector": "Knowledge & media",
        "tasks": ["Membership management", "Donation records", "Volunteer tracking", "Community engagement"],
        "unit": "subscription or completed service", "proof": "Member consent, donation receipt reconciliation and safeguarding records",
        "equipment": "Membership and donor systems with role-based access",
    },
    {
        "id": "enterprise-supergrid", "name": "EnterpriseGrid", "sector": "Super Grids",
        "tasks": ["HR", "Payroll", "Finance", "Accounting", "Procurement", "CRM", "Projects", "Inventory", "POS", "Assets", "Compliance", "Document management"],
        "unit": "accepted subscription or service", "proof": "Role-based records, audit trail and reconciled subscription/payment",
        "equipment": "Shared enterprise modules with tenant isolation",
    },
    {
        "id": "secure-supergrid", "name": "SecureGrid", "sector": "Super Grids",
        "tasks": ["CCTV", "Access control", "Biometrics", "ANPR", "Visitor management", "Incident management", "Smart parking", "Facility management", "IoT sensors"],
        "unit": "accepted installation or managed service", "proof": "Written authorization, lawful processing, safety and customer acceptance",
        "equipment": "Verified security/facility vendors and approved device integrations",
    },
    {
        "id": "mobility-supergrid", "name": "MobilityGrid", "sector": "Super Grids",
        "tasks": ["Fleet management", "Vehicle tracking", "Fuel monitoring", "Cargo tracking", "Driver management", "Route optimization", "Warehouse", "Delivery"],
        "unit": "accepted trip, shipment or subscription", "proof": "Vehicle/order IDs, consented telemetry and delivery acceptance",
        "equipment": "Verified fleet, carrier and logistics integrations",
    },
    {
        "id": "agri-supergrid", "name": "AgriGrid", "sector": "Super Grids",
        "tasks": ["Farm management", "Climate intelligence", "Market access", "Input marketplace", "Produce aggregation", "Storage and supply chain"],
        "unit": "accepted farm service or transaction", "proof": "Farm/provider authorization, verified quantity and transaction evidence",
        "equipment": "Agricultural service partners, approved sensors and compatible robots",
    },
    {
        "id": "energy-supergrid", "name": "EnergyGrid", "sector": "Super Grids",
        "tasks": ["Solar management", "Battery management", "Smart metering", "Mini-grids", "Energy financing referrals", "Carbon monitoring"],
        "unit": "accepted installation, measured service or subscription", "proof": "Meter/inverter evidence, written agreement, customer acceptance and reconciliation",
        "equipment": "Verified energy provider, compatible inverter/meter APIs and qualified installers",
    },
    {
        "id": "power", "name": "PowerGrid", "sector": "Energy",
        "tasks": ["Grid connection inspection", "Power quality monitoring", "Outage reporting", "Meter verification"],
        "unit": "verified inspection or completed service",
        "proof": "Authorized utility work order, calibrated measurement evidence and customer acceptance",
        "equipment": "Qualified electrical personnel and approved, safety-rated instruments",
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
