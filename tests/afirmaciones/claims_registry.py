"""
Documentary Claims Registry (Phase 4).

Each claim from Traianus sources is declared here with a state: ACTIVE
(verified by test), RED (not met; disposition CODE_FIX|DOC_FIX), WP (explicit
scope exclusion in PoC).

The SPEC for this package is docs/development/tests/SPEC-afirmaciones.md.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# State of each claim: ACTIVE | RED | WP. disposition only for RED.
CLAIMS = {
    "CL-C41": {
        "source": "CONTRACTS_AND_PRISMS.md C-4.1",
        "state": "ACTIVE",
        "must": "/telemetry requires token and does not leak full stack traces to anonymous callers.",
    },
    "CL-I5": {
        "source": "PROJECT_IDENTITY.md I-5",
        "state": "ACTIVE",
        "must": "The control plane does not embed a user interface (zero-UI).",
    },
    "CL-I61": {
        "source": "ADR-016",
        "state": "ACTIVE",
        "must": "The control plane does not invoke generative LLMs (zero-LLM).",
    },
    "CL-I62": {
        "source": "I-6.2 / L6",
        "state": "ACTIVE",
        "must": "A provider with dimension greater than the basis is rejected or handled explicitly without breaking projections.",
    },
    "CL-R1": {
        "source": "README R-1 / M4",
        "state": "ACTIVE",
        "must": "The README quickstart starts via traianus-bootstrap (packaged script).",
    },
    "CL-R2": {
        "source": "README R-2 / M4",
        "state": "ACTIVE",
        "must": "The README quickstart documents uvicorn traianus.app:app --host 127.0.0.1.",
    },
    "CL-WP1": {
        "source": "PROJECT_IDENTITY.md WP",
        "state": "ACTIVE",
        "must": "Packages traianus.{core.basis,tda,metrics,replication} do not exist in the PoC (WP exclusion).",
    },
    "CL-TR1": {
        "source": "SPEC-afirmaciones CL-TR1",
        "state": "ACTIVE",
        "must": "The doc → SPEC → test chain has no gaps: every ACTIVE claim has a test and every test references its SPEC.",
    },
    "CL-LIT1": {
        "source": "Topological_Grounding convention",
        "state": "ACTIVE",
        "must": "Topological_Grounding citations exist character-by-character in the cited source file.",
    },
}

# Verified literal quotes (CL-LIT1): (repo-relative path, exact fragment)
LITERAL_QUOTES = [
    ("docs/architecture/ADR/ADR.md",
     "Integration test suites must validate these five invariants on every build pipeline."),
    ("docs/architecture/ARCHITECTURE.md",
     "Deterministic adjacency edges formed strictly where $d(\\mathbf{v}_i, \\mathbf{v}_j) \\leq \\epsilon$"),
    ("traianus/app.py",
     "for j, other in enumerate(vectors) if j != i"),
]


def active_claims() -> dict:
    return {k: v for k, v in CLAIMS.items() if v["state"] == "ACTIVE"}


def red_claims() -> dict:
    return {k: v for k, v in CLAIMS.items() if v["state"] == "RED"}


def resolve(path: str) -> str:
    """Resolve a repo-relative path from the pytest CWD."""
    return path if os.path.isabs(path) else os.path.join(ROOT, path)
