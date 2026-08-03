"""Traianus real invariant verifier (contract mining kit).

Checks the obligations mined from `traianus_poc_obligations.json` against:
  1. The SOURCE CODE (`traianus/app.py`) -- static analysis.
  2. The REAL DATABASE (`traianus.db`) -- data verification.

Verified invariants:
  TR-H4-001  append-only: no UPDATE/REPLACE/DELETE against manifold_nodes (static)
  TR-H4-002  composite PK (id, seq) without duplicates (real data)
  TR-H4-003  contiguous increasing seq per id (real data)
  TR-C1-001  self-projection excluded in auto_calibrate_critical_threshold (static)
  TR-ZT-001  ingress perimeter = text/plain allowlist (static)
  TR-ZT-002  CORS without wildcard (static)

Usage:
  python3 tools/traianus_invariant_verifier.py [path_to_traianus.db]
Exit 0 = all obligations met; exit 1 = findings.
"""

import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PY = REPO_ROOT / "traianus" / "app.py"
DB_PATH = REPO_ROOT / "traianus.db"


def read_app() -> str:
    return APP_PY.read_text(encoding="utf-8")


def check_static(app_code: str, findings: list) -> None:
    # TR-H4-001: destructive statements against manifold_nodes
    destructive = re.findall(
        r"(UPDATE|REPLACE|DELETE)\s+manifold_nodes\b",
        app_code,
        flags=re.IGNORECASE,
    )
    if destructive:
        findings.append(
            f"TR-H4-001 MUST_NOT: destructive statements against manifold_nodes: {destructive}"
        )
    else:
        print("  OK TR-H4-001  append-only manifold_nodes (no UPDATE/REPLACE/DELETE)")

    # TR-C1-001: self-projection exclusion
    has_self_excl = bool(
        re.search(r"for j,\s*other\s+in\s+enumerate\(vectors\)\s+if\s+j\s*!=\s*i", app_code)
    )
    if has_self_excl:
        print("  OK TR-C1-001  self-projection excluded (if j != i)")
    else:
        findings.append("TR-C1-001 MUST: self-projection (i==j) not excluded in auto_calibrate_critical_threshold")

    # TR-ZT-001: text/plain allowlist
    if re.search(r'ALLOWED_INGRESS_TYPES\s*=\s*\{\s*"text/plain"\s*\}', app_code):
        print("  OK TR-ZT-001  text/plain ingress perimeter (allowlist)")
    else:
        findings.append("TR-ZT-001 MUST: ALLOWED_INGRESS_TYPES != {'text/plain'}")

    # TR-ZT-002: CORS without wildcard
    origins_match = re.search(r"ALLOWED_ORIGINS\s*=\s*\[([^\]]*)\]", app_code)
    if origins_match and "*" not in origins_match.group(1):
        print("  OK TR-ZT-002  CORS without wildcard (*)")
    else:
        findings.append("TR-ZT-002 MUST_NOT: CORS with wildcard allow_origins ('*')")


def check_db(db_path: Path, findings: list) -> None:
    if not db_path.exists():
        findings.append(f"Database not found: {db_path}")
        return
    con = sqlite3.connect(str(db_path))
    try:
        # TR-H4-002: no (id, seq) duplicates
        rows = con.execute(
            "SELECT id, seq, COUNT(*) AS c FROM manifold_nodes GROUP BY id, seq HAVING c > 1"
        ).fetchall()
        if rows:
            findings.append(f"TR-H4-002 MUST: duplicate (id,seq) in manifold_nodes: {rows[:5]}")
        else:
            print("  OK TR-H4-002  composite PK (id, seq) without duplicates")

        # TR-H4-003: contiguous increasing seq per id
        ids = con.execute("SELECT DISTINCT id FROM manifold_nodes ORDER BY id").fetchall()
        gaps = []
        for (nid,) in ids:
            seqs = [r[0] for r in con.execute(
                "SELECT seq FROM manifold_nodes WHERE id = ? ORDER BY seq", (nid,)
            )]
            if seqs != list(range(1, len(seqs) + 1)):
                gaps.append((nid, seqs))
        if gaps:
            findings.append(f"TR-H4-003 MUST: gaps/ordering in seq per id: {gaps[:5]}")
        else:
            print(f"  OK TR-H4-003  contiguous seq 1..n per id ({len(ids)} nodes)")
    finally:
        con.close()


def main():
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    print("=== TRAIANUS INVARIANT VERIFIER (PoC v1.0) ===")
    print(f"Source: {APP_PY} | DB: {db_path}")

    findings = []
    check_static(read_app(), findings)
    check_db(db_path, findings)

    if findings:
        print(f"\nRED -- {len(findings)} finding(s):")
        for f in findings:
            print(f"  - {f}")
        sys.exit(1)
    print("\nGREEN -- all obligations met (exit 0)")


if __name__ == "__main__":
    main()
