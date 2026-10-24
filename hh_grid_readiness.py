"""Commercial readiness gates for CEDARS EMPIRE grids.

This module intentionally reports a grid as NOT READY unless the required
commercial evidence is supplied. It does not claim provider, hardware, payment,
regulatory, or database integrations exist.
"""
from __future__ import annotations

from typing import Mapping, Any

REQUIRED_GATES = (
    "legal_entity_and_local_permissions",
    "verified_provider_or_runtime",
    "customer_order_and_contract",
    "delivery_evidence_and_acceptance",
    "durable_records_and_audit",
    "payment_verification_and_reconciliation",
    "security_privacy_and_safety_review",
    "unit_economics_and_support",
)

GATE_LABELS = {
    "legal_entity_and_local_permissions": "Legal / local permissions",
    "verified_provider_or_runtime": "Provider / runtime verified",
    "customer_order_and_contract": "Customer order / contract",
    "delivery_evidence_and_acceptance": "Delivery evidence / acceptance",
    "durable_records_and_audit": "Durable records / audit",
    "payment_verification_and_reconciliation": "Payment / reconciliation",
    "security_privacy_and_safety_review": "Security / privacy / safety",
    "unit_economics_and_support": "Unit economics / support",
}


def evaluate_grid_readiness(
    grid: Mapping[str, Any],
    evidence: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Return evidence-based readiness; absent checks always fail closed."""
    evidence = evidence or {}
    passed = [gate for gate in REQUIRED_GATES if evidence.get(gate) is True]
    missing = [gate for gate in REQUIRED_GATES if evidence.get(gate) is not True]
    ready = not missing
    return {
        "grid_id": str(grid.get("id", "")),
        "grid": str(grid.get("name", "Unnamed grid")),
        "sector": str(grid.get("sector", "Unspecified")),
        "status": "Ready for controlled commercial pilot" if ready else "Not ready — evidence required",
        "gates_passed": len(passed),
        "gates_total": len(REQUIRED_GATES),
        "missing_gates": [GATE_LABELS[gate] for gate in missing],
        "readiness_percent": round(100 * len(passed) / len(REQUIRED_GATES)),
    }


def evaluate_catalog_readiness(catalog: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Catalogue-only view: no persisted evidence means no grid is marked ready."""
    return [evaluate_grid_readiness(grid) for grid in catalog]
