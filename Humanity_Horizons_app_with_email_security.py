        stream_name = st.selectbox("Opportunity", [n for n,_ in revenue_streams])
        category = dict(revenue_streams)[stream_name]
        stage = st.selectbox("Planning status", ["Idea", "Validation needed", "Business case drafted", "Approved to test", "Pilot", "Active", "Paused", "Rejected"])
        estimate = st.text_input("Estimated amount (optional; planning estimate only)")
        currency = st.selectbox("Currency", ["UGX", "USD", "EUR", "GBP", "Other"])
        assumptions = st.text_area("Assumptions, costs, risks and evidence")
        next_step = st.text_input("Next action / owner")
        save_stream = st.form_submit_button("Save revenue opportunity")
    if save_stream:
        db_exec("INSERT INTO revenue_opportunities (id,owner_email,stream_name,category,status,estimated_amount,currency,assumptions,next_step,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), USER_EMAIL, stream_name, category, stage, estimate.strip() or None, currency, assumptions.strip(), next_step.strip(), now_iso(), now_iso()))
        record_event(USER_EMAIL, "revenue_opportunity_created")
        st.success("Planning opportunity saved; no income has been recorded.")
        st.rerun()
    own = db_all("SELECT stream_name,category,status,estimated_amount,currency,assumptions,next_step,updated_at FROM revenue_opportunities WHERE owner_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    st.subheader("My sustainability pipeline")
    if own:
        rdf = pd.DataFrame(own)
        st.dataframe(rdf, use_container_width=True, hide_index=True)
        download_gate("revenue opportunity plan", rdf.to_csv(index=False), "humanity_horizons_revenue_plan.csv", "text/csv", "revenue_plan")
    else:
        st.info("No revenue opportunities have been saved yet.")

# -----------------------------------------------------------------------------
# Report schedule and indicator register — delivery requires external scheduler
# -----------------------------------------------------------------------------
elif page == "Report Automation":
    st.header("Reporting Calendar & Automation")
    st.caption("Configure reporting requirements and maintain a persistent indicator register. This page records schedules; an external scheduled job and email credentials are required to execute and deliver reports automatically.")
    with st.form("indicator_form"):
        project_name = st.text_input("Project / programme")
        indicator_name = st.text_input("Indicator name")
        indicator_type = st.selectbox("Indicator type", ["Output", "Outcome", "Impact", "Process", "Safeguarding / accountability", "Financial"])
        baseline = st.text_input("Baseline")
        target = st.text_input("Target")
        current_value = st.text_input("Current value / latest result")
        unit = st.text_input("Unit (e.g. people, %, UGX)")
        disaggregation = st.text_input("Disaggregation (e.g. sex, age, disability, location; where safe and lawful)")
        data_source = st.text_input("Data source / verification evidence")
        reporting_frequency = st.selectbox("Indicator reporting frequency", ["Monthly", "Quarterly", "Semi-annual", "Annual", "Ad hoc"])
        reporting_period = st.text_input("Reporting period (e.g. 2026-Q4)")
        indicator_notes = st.text_area("Limitations, assumptions and data-quality notes")
        save_indicator = st.form_submit_button("Save indicator record", type="primary")
    if save_indicator:
        if not project_name.strip() or not indicator_name.strip():
            st.error("Project and indicator name are required.")
        else:
            db_exec("INSERT INTO project_indicators (id,owner_email,project_name,indicator_name,indicator_type,baseline,target,current_value,unit,disaggregation,data_source,reporting_frequency,reporting_period,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), USER_EMAIL, project_name.strip(), indicator_name.strip(), indicator_type, baseline.strip(), target.strip(), current_value.strip(), unit.strip(), disaggregation.strip(), data_source.strip(), reporting_frequency, reporting_period.strip(), indicator_notes.strip(), now_iso(), now_iso()))
            record_event(USER_EMAIL, "project_indicator_created")
            st.success("Indicator record saved.")
            st.rerun()
    indicators = db_all("SELECT * FROM project_indicators WHERE owner_email=? ORDER BY updated_at DESC", (USER_EMAIL,))
    st.subheader("Indicator register")
    if indicators:
        idf = pd.DataFrame([{ "Project": x["project_name"], "Indicator": x["indicator_name"], "Type": x["indicator_type"], "Baseline": x["baseline"], "Target": x["target"], "Current value": x["current_value"], "Unit": x["unit"], "Disaggregation": x["disaggregation"], "Data source": x["data_source"], "Frequency": x["reporting_frequency"], "Period": x["reporting_period"], "Notes": x["notes"] } for x in indicators])
        st.dataframe(idf, use_container_width=True, hide_index=True)
        download_gate("indicator register", idf.to_csv(index=False), "humanity_horizons_indicator_register.csv", "text/csv", "indicator_register")
        report = ["HUMANITY HORIZONS — INDICATOR / M&E WORKING REPORT", f"Generated: {now_iso()}", "", "IMPORTANT: Validate every value against source records before external submission.", ""]
        for row in indicators:
            report += [f"Project: {row['project_name']}", f"Indicator: {row['indicator_name']} ({row['indicator_type']})", f"Baseline: {row['baseline'] or 'Not recorded'} | Target: {row['target'] or 'Not recorded'} | Current: {row['current_value'] or 'Not recorded'} {row['unit'] or ''}", f"Period: {row['reporting_period'] or 'Not recorded'} | Frequency: {row['reporting_frequency']}", f"Data source: {row['data_source'] or 'Not recorded'}", f"Disaggregation: {row['disaggregation'] or 'Not recorded'}", f"Data-quality notes: {row['notes'] or 'None recorded'}", ""]
        report_text = "\n".join(report)
        st.text_area("Generated working M&E report", report_text, height=280)
        download_gate("indicator / M&E working report", report_text, "humanity_horizons_me_working_report.txt", key="indicator_me_report")
    else:
        st.info("Add indicator records to begin generating a report from stored project data.")
    st.divider()
    st.subheader("Report delivery schedules")
    with st.form("report_schedule_form"):
        report_name = st.selectbox("Report to schedule", ["Platform operations summary", "Project indicator / M&E report", "Donor feedback summary", "Treasury reconciliation summary"])
        frequency = st.selectbox("Frequency", ["Monthly", "Quarterly", "Semi-annual", "Annual"])
        run_day = st.number_input("Day of month (monthly schedules; default 25)", min_value=1, max_value=28, value=25)
        recipient_email = st.text_input("Delivery recipient email (optional until mail is configured)")
        timezone_name = st.selectbox("Reporting timezone", ["Africa/Kampala", "UTC", "Africa/Nairobi", "Europe/London"])
        enabled = st.checkbox("Enable this schedule", value=True)
        save_schedule = st.form_submit_button("Save report schedule")
    if save_schedule:
        if recipient_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient_email.strip()):
            st.error("Enter a valid recipient email or leave it blank.")
        else:
            db_exec("INSERT INTO report_schedules (id,owner_email,report_name,frequency,run_day,recipient_email,enabled,timezone_name,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), USER_EMAIL, report_name, frequency, int(run_day), recipient_email.strip() or None, int(enabled), timezone_name, now_iso(), now_iso()))
            record_event(USER_EMAIL, "report_schedule_created")
            st.success("Schedule saved. It will not send automatically until a scheduler and delivery provider are configured.")
            st.rerun()
    schedules = db_all("SELECT report_name,frequency,run_day,recipient_email,enabled,timezone_name,created_at FROM report_schedules WHERE owner_email=? ORDER BY created_at DESC", (USER_EMAIL,))
    if schedules:
        st.dataframe(pd.DataFrame(schedules), use_container_width=True, hide_index=True)
    if IS_ADMIN:
        st.subheader("Platform-wide schedules (administrator only)")
        admin_schedules = db_all("SELECT owner_email,report_name,frequency,run_day,recipient_email,enabled,timezone_name,created_at FROM report_schedules ORDER BY created_at DESC LIMIT 500")
        st.dataframe(pd.DataFrame(admin_schedules), use_container_width=True, hide_index=True)

# Unknown page guard
else:
    st.error("This administrator page is not available for the current account.")

st.divider()
st.caption("Humanity Horizons · People, Planet and Peace · Build 1.1. Humanity Horizons owns and maintains its proprietary standards and workforce-readiness framework. Verify source documents, application instructions, CV claims, indicators and legal requirements before relying on an output.")
