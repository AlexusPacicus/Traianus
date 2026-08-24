#!/usr/bin/env python
"""Freeze empirical telemetry summaries into a versioned dataset.

The live experiment artifacts (scratch DBs, telemetry/chromatic JSONs) are
ephemeral under .data/ (gitignored). This tool distills them into the
versioned record data/spinoza/telemetry/<version>.json so LEDGER claims are
auditable from a fresh clone without re-running encoders.

Read-only on inputs; writes exactly one output file. Offline.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT))

from _common import load_labels

RUNS = [
    ("part1_isolated", "part1_god"),
    ("part2_isolated", "part2_mind"),
    ("part3_isolated", "part3_affects"),
    ("part4_isolated", "part4_bondage"),
    ("part5_isolated", "part5_power"),
    ("accumulated_12345", "spinoza_full"),
]

PART_BY_PREFIX = {"PART1": "P1_GOD", "PART2": "P2_MIND", "PART3": "P3_AFFECTS",
                   "PART4": "P4_BONDAGE", "PART5": "P5_POWER"}

TOP_BRIDGES_LIMIT = 10


def part_of(label: str) -> str:
    return PART_BY_PREFIX[label[:5]]


def load_run(stem: str) -> dict:
    telemetry = json.loads(
        (REPO_ROOT / ".data" / f"{stem}_telemetry.json").read_text(encoding="utf-8"))
    chromatic_path = REPO_ROOT / ".data" / f"{stem}_chromatic.json"
    chromatic = (json.loads(chromatic_path.read_text(encoding="utf-8"))
                 if chromatic_path.is_file() else None)
    return {
        "n_nodes": len(telemetry["rows"]),
        "n_edges_persisted": telemetry["n_edges_persisted"],
        "gate_consolidated": sum(
            1 for r in telemetry["rows"] if r["gate_state"] == "consolidated"),
        "sigma2": {k: round(telemetry["summary"][k], 6) for k in
                   ("variance_min", "variance_p50", "variance_p95",
                    "variance_max")},
        "theta_dyn": round(telemetry["theta_dyn"], 6),
        "epsilon": telemetry["epsilon"],
        "chromatic": None if chromatic is None else {
            "sammon_stress_2d": chromatic["sammon"]["stress_2d"],
            "sammon_stress_5d": chromatic["sammon"]["stress_5d"],
            "decompression_gain_pct":
                chromatic["sammon"]["decompression_gain_pct"],
            "collisions": chromatic["collisions"]["count"],
            "collision_rescue_rate": chromatic["collisions"]["rescue_rate"],
            "stylistic_duplicates":
                len(chromatic["stylistic_duplicates"]),
        },
    }


def inter_part_edges(full_db: Path, labels_path: Path) -> dict:
    """Current-state epsilon edges grouped by part pair, plus top bridges."""
    sys.path.insert(0, str(REPO_ROOT))
    import numpy as np

    from traianus.geometry.observables import compute_epsilon_edges

    labels = load_labels(labels_path)

    def part(nid: str) -> str:
        return part_of(labels[nid])

    conn = sqlite3.connect(f"file:{full_db}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT m.id, m.vector_blob, m.projections_json "
            "FROM manifold_nodes m WHERE m.lifecycle_state != 'telemetry_error' "
            "AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 "
            "WHERE m2.id = m.id)").fetchall()
    finally:
        conn.close()
    vectors = {r[0]: np.frombuffer(r[1], dtype=np.float64) for r in rows}
    projections = {r[0]: json.loads(r[2]) for r in rows}

    edges = compute_epsilon_edges(vectors, 0.8)
    intra: dict[str, int] = {}
    inter: dict[str, int] = {}
    cross_bridges = []
    keys = sorted(next(iter(projections.values())),
                  key=lambda k: int(k.rsplit("_", 1)[1]))
    for e in edges:
        s, t = e["source"], e["target"]
        ps, pt = part(s), part(t)
        if ps == pt:
            intra[ps] = intra.get(ps, 0) + 1
        else:
            key = " <-> ".join(sorted((ps, pt)))
            inter[key] = inter.get(key, 0) + 1
            if {ps, pt} == {"P2_MIND", "P3_AFFECTS"}:
                qa, qb = projections[s], projections[t]
                products = [abs(qa.get(k, 0.0) * qb.get(k, 0.0)) for k in keys]
                k_best = int(max(range(len(keys)), key=lambda i: products[i]))
                cross_bridges.append({
                    "pair": f"{s}<->{t}",
                    "labels": [labels[s], labels[t]],
                    "distance": round(e["distance"], 4),
                    "resonance_axis": f"AXIS_{k_best + 1}",
                })
    cross_bridges.sort(key=lambda b: b["distance"])
    return {
        "intra_part_edges": dict(sorted(intra.items())),
        "inter_part_edges": {k: inter[k] for k in sorted(inter)},
        "top_cross_part_bridges": cross_bridges[:TOP_BRIDGES_LIMIT],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=REPO_ROOT / "data" / "spinoza" / "telemetry"
                        / "v1.json")
    args = parser.parse_args()

    payload = {
        "provenance": {
            "source_edition": "Project Gutenberg eBook #3800 (Elwes translation), public domain",
            "encoder": "sentence-transformers all-MiniLM-L6-v2, 384D float32, offline",
            "geodetic_basis": "tests/fixtures/nsm_axes_8.json (epoch PROSTHETIC_NSM_V1)",
            "epsilon_edge": 0.8,
            "note": ("Aggregate summaries distilled from ephemeral .data/ "
                     "artifacts; manifold findings are conditional on this "
                     "representation provider (RH-1 independence untested here)."),
        },
        "runs": {name: load_run(stem) for name, stem in RUNS},
        "inter_part_analysis": inter_part_edges(
            REPO_ROOT / ".data" / "spinoza_full.db",
            REPO_ROOT / ".data" / "spinoza_full_labels.json"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"[+] frozen telemetry: {args.out}")
    print(f"[+] runs summarized: {len(payload['runs'])} | "
          f"inter-part edges: {payload['inter_part_analysis']['inter_part_edges']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
