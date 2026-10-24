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
    .robot-motion-stage{display:flex;align-items:center;justify-content:center;min-height:150px;
      background:radial-gradient(circle at 50% 45%,rgba(214,168,79,.18),rgba(7,29,51,.96) 68%);
      border:1px solid #244E68;border-radius:14px;overflow:hidden;position:relative}
    .robot-orbit{position:absolute;width:118px;height:118px;border:1px solid rgba(214,168,79,.6);
      border-radius:50%;animation:ce-orbit 8s linear infinite}
    .robot-orbit:before{content:"";position:absolute;top:12px;left:17px;width:8px;height:8px;
      border-radius:50%;background:#D6A84F;box-shadow:0 0 12px #D6A84F}
    .robot-avatar{font-size:72px;filter:drop-shadow(0 0 15px rgba(90,196,255,.35));
      animation:ce-robot-float 2.8s ease-in-out infinite;z-index:1}
    .robot-scan{position:absolute;left:12%;right:12%;height:2px;background:#60D5FF;
      box-shadow:0 0 12px #60D5FF;opacity:.6;animation:ce-scan 3s ease-in-out infinite}
    @keyframes ce-robot-float{0%,100%{transform:translateY(4px) rotate(-2deg)}50%{transform:translateY(-8px) rotate(2deg)}}
    @keyframes ce-orbit{to{transform:rotate(360deg)}}
    @keyframes ce-scan{0%,100%{top:22%;opacity:.15}50%{top:76%;opacity:.8}}
    .robot-live-label{position:absolute;bottom:10px;left:12px;color:#DCEAF3;font-size:9px;letter-spacing:1.2px;font-weight:800}
    </style>
    <div class="robot-hero">
      <div style="font-size:11px;letter-spacing:2px;font-weight:800;color:#E7C77D">CEDARS EMPIRE · ROBOTICS</div>
      <div style="font-size:22px;font-weight:850;color:#fff;margin-top:5px">Robot Operations</div>
      <p>Animated simulation view · evidence-led tasks · safety-gated activation</p>
    </div>
    <div class="robot-motion-stage" aria-label="Robot motion simulation">
      <div class="robot-orbit"></div><div class="robot-scan"></div>
      <div class="robot-avatar">🤖</div>
      <div class="robot-live-label">VISUAL SIMULATION ONLY · NO HARDWARE CONNECTED</div>
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
