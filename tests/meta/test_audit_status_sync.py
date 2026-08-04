"""
Audit status truth reconciliation (Action Plan 2026-08-03, Phase 1).

Normative (RFC 2119): the remediation status table in TRAIANUS_AUDIT.md MUST
match the verified working tree (AGENTS.md Invariant 1 — audit
synchronization). String-containment assertions on row markers; new IDs are
added to the mapping as their audit row flips to Resolved (Phase 2/3/4/7).

Normative: docs/archive/legacy_docs/development/tests/SPEC-template.md
Coverage: AUDIT-SYNC
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "TRAIANUS_AUDIT.md"

# IDs verified in code + tests BEFORE this cycle (passes now).
RESOLVED = {"C1", "H1", "H2", "H3", "M3", "M4", "M5", "M6", "M7"}
# IDs verified in the working tree but whose audit row is STALE (Phase 1 flips).
TO_RESOLVE = {"H4", "H5", "L2", "L5", "L6"}
# IDs still pending (M1/M2/M8 resolved later in this cycle; L3/L4 deferred).
OPEN = {"M1", "M2", "M8", "L3", "L4"}


def _status_rows() -> dict[str, str]:
    """Parses the Remediation Status table rows {ID: status+evidence text}."""
    text = AUDIT.read_text(encoding="utf-8")
    header = re.search(r"^\| ID \| Status \| Evidence \|\s*$", text, re.M)
    assert header, "TRAIANUS_AUDIT.md status table header not found (format changed?)"
    section = text[header.end():]
    end = re.search(r"^## ", section, re.M)
    if end:
        section = section[: end.start()]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        m = re.match(r"^\|\s*([A-Z]{1,2}\d+)\s*\|\s*(.*?)\s*\|\s*$", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def test_audit_status_rows_present():
    """AUDIT-SYNC: every mapped ID has a status row in TRAIANUS_AUDIT.md."""
    rows = _status_rows()
    for rid in RESOLVED | TO_RESOLVE | OPEN:
        assert rid in rows, f"status row {rid} missing from TRAIANUS_AUDIT.md"


def test_audit_status_resolved_rows_match_code():
    """AUDIT-SYNC: code-verified IDs MUST be marked ✅ Resolved."""
    rows = _status_rows()
    stale = [rid for rid in RESOLVED | TO_RESOLVE if "✅ **Resolved**" not in rows[rid]]
    assert not stale, f"audit rows not marked Resolved: {stale}"


def test_audit_status_open_rows_match_code():
    """AUDIT-SYNC: still-pending IDs MUST be marked Open."""
    rows = _status_rows()
    wrong = [rid for rid in OPEN if "Open" not in rows[rid]]
    assert not wrong, f"audit rows should still be Open: {wrong}"
