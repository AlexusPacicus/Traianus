"""R7/INV-8 (REMEDIATION-01 Delta3): every regression test AUDIT.md cites as
evidence must exist. A name-level cross-check against the test functions
defined under tests/ -- the citation is what a reader greps for, so a name
that resolves to nothing is an unverifiable claim."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CITED_TEST = re.compile(r"`(test_[A-Za-z0-9_]+)`")


def _defined_test_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "tests").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names |= {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        }
    return names


def test_all_cited_test_names_exist():
    audit = (ROOT / "docs" / "audit" / "AUDIT.md").read_text(encoding="utf-8")
    cited = set(CITED_TEST.findall(audit))
    assert cited, "AUDIT.md cites no tests; the pattern or the document changed"
    missing = sorted(cited - _defined_test_names())
    assert not missing, f"AUDIT.md cites tests that do not exist: {missing}"
