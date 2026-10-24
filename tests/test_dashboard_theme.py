from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_native_streamlit_theme_has_non_plain_cedars_palette():
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    theme = config["theme"]
    assert theme["base"] == "light"
    assert theme["primaryColor"] == "#0A2342"
    assert theme["backgroundColor"] == "#FFFFFF"
    assert theme["secondaryBackgroundColor"] == "#F4F7FB"
    assert theme["textColor"] == "#0A2342"


def test_dashboard_branding_css_and_components_remain_in_app():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    for marker in (
        ".ce-dashboard-intro-layout",
        ".ce-dashboard-robot",
        ".ce-business-metric",
        ".ce-grid-card",
        "SERVICE GRID PORTFOLIO",
    ):
        assert marker in source, f"Missing dashboard theme marker: {marker}"


def test_single_landing_page_and_ai_notices_are_scoped_to_ai_page():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Overview": ["Dashboard"],' in source
    assert '"Overview": ["Dashboard", "Investor Landing"]' not in source
    assert 'st.caption("AI: connected" if OPENAI_API_KEY else "AI: local structured mode (API key not configured)")' in source
    assert 'if page == "AI Business Scenario Lab":' in source
    assert 'st.caption("AI Real Business Scenarios")' in source
    assert '<div class="ce-dashboard-intro ce-dashboard-intro-layout">' not in source
    assert '<div class="ce-dashboard-intro-title">Business dashboard</div>' not in source
    assert 'st.info("Integrity rule: scenarios, leads, estimates and planned contracts are not revenue.' in source
    # The AI status must not be emitted in the shared account/header section.
    header_start = source.index('st.divider()\n\n# Cedars Empire: real-business scenario workspace.')
    ai_notice = source.index('st.caption("AI: connected" if OPENAI_API_KEY else "AI: local structured mode (API key not configured)")')
    assert ai_notice > header_start
