"""
Parsing library for normative SPECs and test headers (Phase 3).

Provides tests/meta/ guardians with:
- parse_spec_ids: normative IDs (lines "- **ID** MUST...") of each SPEC.
- iter_test_files: test files subject to guardians.
- read_header / parse_header_ids: normative header (Normative/Coverage).
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC_DIR = os.path.join(ROOT, "docs", "development", "tests")

SPEC_FILES = {
    "global": "SPEC-global.md",
    "ingesta": "SPEC-ingesta.md",
    "consolidacion": "SPEC-consolidacion.md",
    "relaciones": "SPEC-relaciones.md",
    "mutacion": "SPEC-mutacion.md",
    "observabilidad": "SPEC-observabilidad.md",
    "bootstrap": "SPEC-bootstrap.md",
    "afirmaciones": "SPEC-afirmaciones.md",
    "security": "SPEC-security.md",
}

# SPECs whose MUSTs already have test coverage. The 1:1 traceability guardian
# iterates ONLY these; the rest activate when their phase implements them:
# Phase 4 -> afirmaciones; Phase 5 -> security.
ACTIVE_SPECS = [
    "global",
    "ingesta",
    "consolidacion",
    "relaciones",
    "mutacion",
    "observabilidad",
    "bootstrap",
    "afirmaciones",
    "security",
]

_ID_RE = re.compile(r"^\s*-\s*\*\*([A-Z0-9-]+)\*\*\s+(MUST|MUST NOT|SHOULD)", re.M)

EXCLUDED_DIRS = {"__pycache__", "helpers", "fixtures", "meta"}


def parse_spec_ids(spec_name: str) -> set[str]:
    """Returns the canonical set of normative IDs of a SPEC.

    Only the 'Normative requirements' section is parsed: requirements declared
    under a later section (e.g. 'Planificados (Fase 6)') are NOT normative
    until their phase activates them.
    """
    path = os.path.join(SPEC_DIR, SPEC_FILES[spec_name])
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^##\s+Normative requirements", text, re.M)
    if m:
        text = text[m.end():]
        nxt = re.search(r"^##\s+", text, re.M)
        if nxt:
            text = text[: nxt.start()]
    ids = {m.group(1) for m in _ID_RE.finditer(text)}
    if not ids:
        raise AssertionError(f"SPEC {spec_name} does not declare parseable normative requirements")
    return ids


def norm_id(value: str) -> str:
    """Normalizes an ID for comparison: uppercase, no hyphens."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def iter_test_files(root: str):
    """Iterates test files subject to guardians (excludes tooling)."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for fn in sorted(filenames):
            if fn.startswith("test_") and fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def read_header(path: str) -> str:
    """Returns the docstring header (first triple-quote block) of the file."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r'\s*"""(.*?)"""', text, re.S)
    return m.group(1) if m else ""


def parse_header_ids(header: str, prefix: str = "Coverage:") -> set[str]:
    """Parses the ID list declared after the prefix (e.g. 'Coverage:')."""
    ids: set[str] = set()
    for line in header.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            rest = line[len(prefix):].strip()
            ids |= {tok.strip() for tok in rest.split(",") if tok.strip()}
    return ids


def has_rfc2119_keyword(header: str) -> bool:
    return any(kw in header for kw in ("MUST", "MUST NOT", "SHOULD"))
