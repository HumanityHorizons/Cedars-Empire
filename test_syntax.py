from pathlib import Path
import ast

def test_app_parses():
    source = Path(__file__).parents[1] / "app.py"
    ast.parse(source.read_text(encoding="utf-8"))
