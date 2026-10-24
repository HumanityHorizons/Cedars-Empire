"""Safety and completeness tests for the CEDARS EMPIRE grid registry.

These tests validate registry metadata only. They do not certify hosted database
persistence, external providers, hardware telemetry, or real-money settlement.
"""
from hh_grid_marketplace import GRID_CATALOG


def test_grid_catalog_has_unique_ids_and_names():
    ids = [grid["id"] for grid in GRID_CATALOG]
    names = [grid["name"] for grid in GRID_CATALOG]
    assert len(ids) >= 40
    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))


def test_all_five_supergrids_are_registered():
    names = {grid["name"] for grid in GRID_CATALOG}
    assert {"EnterpriseGrid", "SecureGrid", "MobilityGrid", "AgriGrid", "EnergyGrid"} <= names


def test_original_and_new_business_grids_are_present():
    names = {grid["name"] for grid in GRID_CATALOG}
    expected = {
        "SecurityGrid", "WorkforceGrid", "FinanceGrid", "CommerceGrid",
        "ConnectGrid", "CloudGrid", "DataGrid", "FacilityGrid", "FleetGrid",
        "LogisticsGrid", "PowerGrid", "ClimateGrid", "AgricultureGrid",
        "CityGrid", "GovGrid", "HealthGrid", "EduGrid", "ServiceGrid",
        "ContractorGrid", "TalentGrid", "AIGrid", "RobotGrid",
        "KnowledgeGrid", "MediaGrid", "CommunityGrid",
        "Shelter Grid", "Energy Grid", "Cleaning Grid", "Data & AI Grid",
        "Mobility Grid", "Food & Water Grid", "Care Grid",
    }
    assert expected <= names


def test_each_grid_has_task_evidence_and_equipment_requirements():
    for grid in GRID_CATALOG:
        assert grid["id"].strip()
        assert grid["name"].strip()
        assert grid["sector"].strip()
        assert grid["tasks"]
        assert grid["unit"].strip()
        assert grid["proof"].strip()
        assert grid["equipment"].strip()


def test_registry_does_not_claim_unverified_live_operations():
    # Live claims must come from separate verified provider/task/payment records.
    statuses = __import__("hh_grid_marketplace").GRID_STATUSES
    assert "Discovery only" in statuses
    assert "Live — evidence verified" in statuses
    assert "Paused" in statuses
