from hh_grid_marketplace import GRID_CATALOG
from hh_grid_readiness import REQUIRED_GATES, evaluate_catalog_readiness, evaluate_grid_readiness


def test_catalogued_grids_are_not_misrepresented_as_live():
    rows = evaluate_catalog_readiness(GRID_CATALOG)
    assert len(rows) == len(GRID_CATALOG)
    assert rows
    assert all(row["status"] == "Not ready — evidence required" for row in rows)
    assert all(row["gates_passed"] == 0 for row in rows)


def test_grid_only_becomes_pilot_ready_when_every_gate_has_evidence():
    grid = GRID_CATALOG[0]
    evidence = {gate: True for gate in REQUIRED_GATES}
    row = evaluate_grid_readiness(grid, evidence)
    assert row["status"] == "Ready for controlled commercial pilot"
    assert row["readiness_percent"] == 100
    assert row["missing_gates"] == []


def test_missing_or_false_evidence_fails_closed():
    grid = GRID_CATALOG[0]
    evidence = {gate: True for gate in REQUIRED_GATES}
    evidence[REQUIRED_GATES[0]] = False
    row = evaluate_grid_readiness(grid, evidence)
    assert row["status"] == "Not ready — evidence required"
    assert row["readiness_percent"] < 100
    assert row["missing_gates"]
