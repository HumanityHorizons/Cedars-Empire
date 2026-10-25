from pathlib import Path
import ast
import re


def test_workforce_target_is_250_million_and_explicitly_planned():
    source = Path("hh_robot_dashboard.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = next(
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(name, ast.Name) and name.id == "WORKER_TARGET" for name in node.targets)
        and isinstance(node.value, ast.Constant)
    )
    assert target == 250_000_000
    assert "long-term target" in source
    assert "VISUAL SIMULATION ONLY" in source
    assert "not the number of deployed workers" in source


def test_website_assembly_plan_covers_release_gates_and_core_pages():
    plan = Path("SITE_ASSEMBLY_PLAN.md").read_text(encoding="utf-8")
    for required in (
        "Shared shell",
        "Member-facing pages",
        "Administrator-only Command Center",
        "Authentication",
        "Persistence",
        "Payments",
        "Revenue integrity",
        "production promotion",
    ):
        assert required.lower() in plan.lower()
