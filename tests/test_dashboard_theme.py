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
        "CEDARS EMPIRE · BUSINESS OVERVIEW",
        "SERVICE GRID PORTFOLIO",
    ):
        assert marker in source, f"Missing dashboard theme marker: {marker}"
