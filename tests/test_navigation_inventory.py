from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_application_source_compiles_and_has_one_navigation_shell():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'with st.container(key="ce_locked_header")' in source
    assert 'horizontal=True, label_visibility="collapsed"' in source
    assert 'ce-dashboard-intro-title' in source
    assert 'ce-dashboard-robot' in source


def test_business_navigation_includes_grids_and_robot_simulation():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    expected = [
        "World Grid Marketplace",
        "Cleaning Grid",
        "Shelter & Accommodation Grid",
        "Energy & Utilities Grid",
        "AI Training & Data Operations",
        "Robot Operations Dashboard",
        "Customer & Client Management",
        "Calendar & Events",
        "Live Studio",
        "Work & Contracts",
        "Earnings & Wallet",
        "Deposit & Packages",
        "Withdrawals & Full KYC",
        "Staking & Compounding",
        "Referral Program",
        "AI Business Scenario Lab",
        "Business Reports",
    ]
    for label in expected:
        assert f'"{label}"' in source, f"Missing navigation label: {label}"
    assert 'render_grid_marketplace()' in source
    assert 'render_robot_dashboard()' in source


def test_robot_motion_is_explicitly_simulated_not_live_hardware():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    robot_source = (ROOT / "hh_robot_dashboard.py").read_text(encoding="utf-8")
    assert "@keyframes ce-robot-float" in source
    assert "@keyframes ce-orbit" in source
    assert "VISUAL SIMULATION ONLY" in robot_source
    assert "NO HARDWARE CONNECTED" in robot_source


def test_dashboard_route_and_quick_actions_use_registered_business_navigation():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Dashboard": "Dashboard"' in source
    assert '"Account": ["My Work & Wallet", "My Tasks"]' in source
    assert '("Explore business grids", "World Grid Marketplace"' in source
    assert '("Manage earnings", "Earnings & Wallet"' in source
    assert 'st.session_state["ce_top_menu"] = destination_group' in source
    assert 'st.session_state["ce_sub_menu"] = destination' in source
    assert "Switch to NGO Operations" not in source


def test_signup_choices_do_not_offer_retired_ngo_account_category():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "NGO / civil society organization" not in source
    assert '["Individual", "Business / private sector", "Public institution", "Research / academic", "Other"]' in source


def test_dashboard_shows_grid_cards_and_uses_single_brand_shell():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert source.count('with st.container(key="ce_locked_header")') == 1
    assert 'st.markdown(\'<div class="ce-section-label">EXPLORE THE BUSINESS GRIDS</div>\'' in source
    for label in [
        "World Grid Marketplace",
        "Cleaning Grid",
        "Shelter & Accommodation Grid",
        "Energy & Utilities Grid",
        "AI Training & Data Operations",
        "Robot Operations Dashboard",
    ]:
        assert f'("{label}"' in source or f'"{label}"' in source
    internal = source.split("INTERNAL_ONLY_PAGES = {", 1)[1].split("}", 1)[0]
    for member_grid in [
        "Cleaning Grid",
        "Shelter & Accommodation Grid",
        "Energy & Utilities Grid",
        "AI Training & Data Operations",
    ]:
        assert f'"{member_grid}"' not in internal
    assert "Your business at a glance" in source
    assert "CEDARS EMPIRE · BUSINESS OVERVIEW" in source
