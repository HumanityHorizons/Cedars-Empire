"""Robot-first operations dashboard for CEDARS EMPIRE.

This is an honest readiness dashboard. It displays the registered robot grids in
standby; it does not imply live hardware connectivity, stored tasks, or payments.
"""
import streamlit as st
from hh_robotics import robot_grid_catalog

STATUS = {
    "standby": ("🟠", "STANDBY"),
    "registered": ("🔵", "REGISTERED"),
    "connected": ("🟢", "CONNECTED — VERIFY INTEGRATION"),
    "maintenance": ("🟡", "MAINTENANCE"),
    "blocked": ("🔴", "BLOCKED"),
}

def render_robot_dashboard() -> None:
    st.markdown("""
    <style>
    .robot-hero{background:linear-gradient(120deg,#071D33,#123D60 68%,#1B5B66);
      border:1px solid #244E68;border-bottom:4px solid #D6A84F;border-radius:16px;
      padding:26px;margin-bottom:18px;color:#fff}
    .robot-hero h1{color:#fff!important;margin:0;font-size:30px}
    .robot-hero p{color:#DCEAF3!important;margin:8px 0 0}
    .robot-card{background:#fff;border:1px solid #D9E0E7;border-top:3px solid #D6A84F;
      border-radius:12px;padding:16px;min-height:130px;margin-bottom:10px}
    .robot-name{font-size:16px;font-weight:800;color:#0A2540}
    .robot-state{font-size:11px;font-weight:800;letter-spacing:.7px;margin-top:10px}
    .robot-meta{font-size:12px;color:#526579;margin-top:8px}
    </style>
    <div class="robot-hero">
      <div style="font-size:11px;letter-spacing:2px;font-weight:800;color:#E7C77D">CEDARS EMPIRE · ROBOTICS</div>
      <h1>Robot Operations Dashboard</h1>
      <p>Robotics grid readiness · evidence-led tasks · safety-gated activation</p>
    </div>
    """, unsafe_allow_html=True)
    catalog = robot_grid_catalog()
    connected = sum(1 for item in catalog if item["status"] == "connected")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Robot grids", len(catalog))
    c2.metric("Connected", connected)
    c3.metric("Standby", sum(1 for item in catalog if item["status"] == "standby"))
    c4.metric("Verified payments", "Not connected")
    st.caption("Readiness only. No physical robot is connected and no income or payment is claimed by this dashboard.")
    st.subheader("Robot grid register")
    cards = st.columns(2)
    for index, item in enumerate(catalog):
        emoji, label = STATUS.get(item["status"], ("⚪","NOT CONFIGURED"))
        with cards[index % 2]:
            st.markdown(f"""
            <div class="robot-card">
              <div class="robot-name">{item["name"]}</div>
              <div class="robot-state">{emoji} {label}</div>
              <div class="robot-meta">Hardware verification: pending<br>Safety review: pending<br>Task persistence: not configured</div>
            </div>
            """, unsafe_allow_html=True)
    st.subheader("Activation gates")
    st.dataframe([
        {"Gate":"Hardware identity and firmware","Status":"Pending"},
        {"Gate":"Emergency stop and safe-stop validation","Status":"Pending"},
        {"Gate":"Operator permissions and site acceptance","Status":"Pending"},
        {"Gate":"Durable task and evidence storage","Status":"Pending"},
        {"Gate":"Independent payment verification","Status":"Pending"},
    ], use_container_width=True, hide_index=True)
    st.info("Grid indicators remain on standby until the corresponding checks are implemented, recorded and independently verified.")
