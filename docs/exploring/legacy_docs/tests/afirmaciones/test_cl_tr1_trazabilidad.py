"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-TR1: the doc → SPEC → test chain has no gaps: every ACTIVE
claim has a test and every test references its SPEC (full traceability).

This is the meta-guardian of claims: derives actual coverage from
test names (test_afirmaciones_CL_*) and compares with the registry.
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-TR1"""
import os
import re
import ast

from tests.afirmaciones.claims_registry import CLAIMS, active_claims, ROOT

AFIRM_DIR = os.path.join(ROOT, "tests", "afirmaciones")


def _coverage_from_tests() -> set[str]:
    covered: set[str] = set()
    for fn in sorted(os.listdir(AFIRM_DIR)):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        path = os.path.join(AFIRM_DIR, fn)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_afirmaciones_"):
                m = re.match(r"test_afirmaciones_(CL_[A-Z]+\d+)", node.name)
                if m:
                    covered.add(m.group(1).upper().replace("_", "-"))
    return covered


def test_afirmaciones_CL_TR1_every_active_claim_has_test():
    covered = _coverage_from_tests()
    missing = set(active_claims()) - covered
    assert not missing, f"CL-TR1 MUST: ACTIVE claims without test -> {sorted(missing)}"


def test_afirmaciones_CL_TR1_valid_states():
    for cid, claim in CLAIMS.items():
        assert claim["state"] in {"ACTIVE", "RED", "WP"}, f"{cid}: invalid state"
        if claim["state"] == "RED":
            assert "disposition" in claim and claim["disposition"] in {"CODE_FIX", "DOC_FIX"}, (
                f"{cid}: RED requires disposition CODE_FIX|DOC_FIX"
            )
