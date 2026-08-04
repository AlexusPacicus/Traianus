"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-WP1: packages traianus.{core.basis,tda,metrics,replication} do NOT
exist in the PoC (WP exclusion). The PoC substrate lives in traianus/app.py and
traianus/bootstrap.py without representation subpackages.
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-WP1"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXCLUDED_PACKAGES = ["core.basis", "core.tda", "core.metrics", "core.replication"]


def test_afirmaciones_CL_WP1_excluded_packages_do_not_exist():
    pkg_root = ROOT / "traianus"
    assert pkg_root.is_dir()
    for pkg in EXCLUDED_PACKAGES:
        parts = pkg.split(".")
        path = pkg_root.joinpath(*parts)
        assert not path.exists(), f"CL-WP1 MUST NOT: traianus.{pkg} exists in the PoC"
        assert not (ROOT / "traianus" / parts[0]).exists(), (
            f"CL-WP1 MUST NOT: traianus.{parts[0]} exists as a package"
        )


def test_afirmaciones_CL_WP1_expected_poc_modules():
    src_files = {p.name for p in (ROOT / "traianus").glob("*.py")}
    assert {"app.py", "bootstrap.py", "__init__.py"} <= src_files
