"""
Endpoint and generics registry by block (Phase 0).

The 6 domain blocks → HTTP endpoints → applicable generics catalog
(G1–G9). This registry is the single source of truth for block
parametrization of `tests/genericos/` and `tests/bloques/<x>/` skeletons.
"""
from __future__ import annotations

BLOCKS = [
    "ingestion",
    "consolidation",
    "relations",
    "mutation",
    "observability",
    "bootstrap",
]

# method, path template (keys = path params)
ENDPOINTS_BY_BLOCK: dict[str, list[tuple[str, str]]] = {
    "ingestion": [("post", "/ingesta")],
    "consolidation": [("post", "/nodos/{node_id}/consolidar")],
    "relations": [("get", "/relations"), ("post", "/relations")],
    "mutation": [("post", "/mutate/{new_symbol}")],
    "observability": [("get", "/nodos"), ("get", "/telemetry")],
    "bootstrap": [],  # no HTTP surface: covered by helpers/CLI
}

# Generics applicable to each block (parametrization by block).
GENERICS_BY_BLOCK: dict[str, list[str]] = {
    "ingestion": ["G1", "G2", "G3", "G4", "G6", "G7"],
    "consolidation": ["G1", "G2", "G3", "G5", "G7", "G8"],
    "relations": ["G1", "G3", "G5", "G8"],
    "mutation": ["G1", "G3", "G5", "G8"],
    "observability": ["G1", "G2", "G3", "G4", "G5", "G7"],
    "bootstrap": ["G3", "G6", "G7", "G8"],
}

# Generic catalog G1–G9 (normative spec; see docs/exploring/legacy_docs/development/tests/SPEC-global.md)
GENERIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "G1": {
        "name": "authentication",
        "finding": "H3",
        "must": "Every route that mutates state or exposes sensitive observability MUST require the operator token; without valid token → 401.",
    },
    "G2": {
        "name": "CORS enumerated",
        "finding": "H3",
        "must": "CORS policy MUST NOT use wildcard with credentials; allowed origins MUST be explicitly enumerated.",
    },
    "G3": {
        "name": "WAL",
        "finding": "L2",
        "must": "Every handler that opens the DB MUST execute PRAGMA journal_mode=WAL before operating.",
    },
    "G4": {
        "name": "no-fake-200",
        "finding": "H1/M5",
        "must": "A persistence/DB failure MUST NOT return a synthetic 200; MUST propagate noisy 5xx.",
    },
    "G5": {
        "name": "append-only",
        "finding": "H4/ADR-025#1",
        "must": "Node history MUST be append-only: every transition INSERTS a revision with increasing seq; UPDATE/REPLACE/DELETE on manifold_nodes prohibited.",
    },
    "G6": {
        "name": "offline",
        "finding": "M3",
        "must": "The encoder MUST be built with local_files_only=True and HF_HUB_OFFLINE=1; no network downloads at runtime.",
    },
    "G7": {
        "name": "determinism",
        "finding": "M1",
        "must": "Given the same initial state and same inputs, the projections and resulting state MUST be identical (deterministic operations).",
    },
    "G8": {
        "name": "contracts/ADR-007",
        "finding": "ADR-007",
        "must": "Pydantic contracts MUST validate rigidly; the glyph (toon_factor) MUST be a single character.",
    },
    "G9": {
        "name": "Zero-Trust TridenGuard",
        "finding": "AGENTS.md §2.3",
        "must": "The TridenGuard gate MUST block fragments with fetch/axios/urllib.request/requests and verify literal grounding.",
    },
}


def generics_for(block: str) -> list[str]:
    return list(GENERICS_BY_BLOCK.get(block, []))


def endpoints_for(block: str) -> list[tuple[str, str]]:
    return list(ENDPOINTS_BY_BLOCK.get(block, []))
