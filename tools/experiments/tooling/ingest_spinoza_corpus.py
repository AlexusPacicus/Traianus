#!/usr/bin/env python
"""Ingest the frozen Spinoza Part II corpus into a SCRATCH Traianus DB.

Reads data/spinoza/part2_mind_manifest.json ({label -> chunk}, reading
order) and runs every sentence through the REAL representation pipeline:
offline encoder -> ingress binary invariant -> L6 dimension check ->
strict L2 normalization -> spectral projection over the ACTIVE geodetic
epoch -> append-only node revision + deterministic E_n persistence.

The substrate at repo root is never touched: storage.DB_PATH is redirected
to the scratch DB (.data/ by default, gitignored). The geodetic basis is
copied VERBATIM (same BLOBs, same epoch) from the root DB so projections
stay comparable with the frozen tissue.

Node ids are NODE_<k> in reading order (1-based): the numeric suffix keeps
tools/analyze_bridges.py reading-order logic working. The label <-> node_id
map is written to .data/spinoza_part2_labels.json (ephemeral work artifact;
labels are neutral metadata, never embedded).

Offline only: no network primitives (AGENTS.md 2.1). Append-only writes
(AGENTS.md 4.1): if the scratch DB already contains nodes, abort.
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_MANIFEST = REPO_ROOT / "data" / "spinoza" / "part2_mind_manifest.json"
DEFAULT_SCRATCH_DB = str(REPO_ROOT / ".data" / "spinoza_part2.db")

# Frozen dataset conventions per Ethics part (data/spinoza/).
CORPUS_STEMS = {1: "part1_god", 2: "part2_mind", 3: "part3_affects", 4: "part4_bondage", 5: "part5_power"}


def corpus_stem(part: int) -> str:
    return CORPUS_STEMS[part]


def scratch_db_path() -> str:
    return DEFAULT_SCRATCH_DB


def node_id(index: int) -> str:
    """Reading-order node id; numeric suffix for analyze_bridges compat."""
    return f"NODE_{index}"


def load_manifest(path: Path) -> list[tuple[str, str]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return list(manifest.items())


def telemetry_summary(rows: list[tuple[str, str, float]]) -> dict:
    """Variance statistics over (node_id, label, variance) rows."""
    if not rows:
        raise ValueError("no telemetry rows to summarize")
    variances = sorted(row[2] for row in rows)
    n = len(variances)

    def pct(p: float) -> float:
        k = (n - 1) * p
        lo, hi = int(k), min(int(k) + 1, n - 1)
        frac = k - lo
        return variances[lo] * (1 - frac) + variances[hi] * frac

    return {
        "count": n,
        "variance_min": variances[0],
        "variance_p50": pct(0.50),
        "variance_p95": pct(0.95),
        "variance_max": variances[-1],
    }


def _load_axes_from_fixture(fixture: Path) -> list[tuple]:
    """Loads the frozen committed geodetic basis (tests/fixtures/nsm_axes_8.json).

    Deterministic genesis: same BLOBs as the frozen harness artifact, tagged
    with the canonical epoch provenance (AGENTS.md 3.3).
    """
    entries = json.loads(fixture.read_text(encoding="utf-8"))
    import numpy as np

    return [(e["id"], e["simbolo"], e["tag"],
             np.asarray(e["vector"], dtype=np.float64).tobytes(),
             "PROSTHETIC_NSM_V1")
            for e in entries]


def _copy_basis(scratch_db: str, basis_db: Path | None, fixture: Path) -> tuple[list[tuple], str]:
    """Resolves the geodesic basis for the scratch DB.

    Prefers a verbatim copy of an existing substrate (--basis-db, read-only
    on the source); falls back to the frozen committed fixture (deterministic
    genesis). INSERT-only on the target via storage.insert_axis.
    Returns (axis_rows, epoch_tag).
    """
    import traianus.storage as storage

    if basis_db is not None:
        src = sqlite3.connect(f"file:{basis_db}?mode=ro", uri=True)
        try:
            cols = [r[1] for r in src.execute(
                "PRAGMA table_info(geodesic_axes)").fetchall()]
            rows = ([] if not cols else src.execute(
                "SELECT id, simbolo, tag, vector_blob, epoch_provenance "
                "FROM geodesic_axes ORDER BY id").fetchall())
        finally:
            src.close()
        if rows:
            epochs = {row[4] for row in rows}
            if len(epochs) > 1:
                latest = max(epochs)
                rows = [row for row in rows if row[4] == latest]
            return rows, rows[0][4]
        print(f"[i] {basis_db} has no usable geodesic_axes; "
              f"falling back to frozen fixture {fixture}")
    rows = _load_axes_from_fixture(REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
                                   if fixture is None else fixture)
    with storage.get_db_connection() as conn:
        for axis_id, simbolo, tag, blob, provenance in rows:
            storage.insert_axis(conn, axis_id, simbolo, tag, blob, provenance)
    return rows, rows[0][4]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None,
                        help="explicit manifest path (overrides --part)")
    parser.add_argument("--part", type=int, choices=sorted(CORPUS_STEMS),
                        default=None,
                        help="Ethics part to ingest in isolation "
                             "(default: 2)")
    parser.add_argument("--accumulate", action="store_true",
                        help="ingest ALL parts (1+2+3) in reading order into "
                             ".data/spinoza_full.db for cross-part analysis")
    parser.add_argument("--db", type=Path, default=None,
                        help="scratch DB path (default: derived from --part)")
    parser.add_argument("--basis-db", type=Path, default=None,
                        help="existing substrate to copy the frozen basis from "
                             "(verbatim); omitted = use the committed fixture")
    parser.add_argument("--basis-fixture", type=Path, default=None,
                        help="frozen geodetic basis JSON fixture "
                             "(default: tests/fixtures/nsm_axes_8.json)")
    parser.add_argument("--limit", type=int, default=None,
                        help="ingest only the first N chunks (smoke run)")
    args = parser.parse_args()

    import numpy as np

    import traianus.storage as storage
    from traianus.app import (
        _encode_vector,
        get_geodetic_matrix_db,
        serialize_vector,
    )
    from traianus.config import resolve_epsilon_edge
    from traianus.core import evaluate_gate_v01, calibrate_critical_threshold

    if args.accumulate:
        parts = sorted(CORPUS_STEMS)
        stem = "spinoza_full"
        manifests = [REPO_ROOT / "data" / "spinoza"
                     / f"{CORPUS_STEMS[p]}_manifest.json" for p in parts]
    else:
        part = args.part if args.part is not None else 2
        stem = CORPUS_STEMS[part]
        manifests = [args.manifest or (REPO_ROOT / "data" / "spinoza"
                                       / f"{stem}_manifest.json")]
    db_path = args.db or (REPO_ROOT / ".data" / f"{stem}.db")
    for manifest in manifests:
        if not manifest.is_file():
            print(f"ERR: manifest not found: {manifest}", file=sys.stderr)
            return 2
    chunks: list[tuple[str, str]] = []
    for manifest in manifests:
        chunks.extend(load_manifest(manifest))
    if args.limit is not None:
        chunks = chunks[:args.limit]

    storage.DB_PATH = str(db_path)
    Path(storage.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    storage.init_db()

    with storage.get_db_connection() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM manifold_nodes").fetchone()[0]
    if existing:
        print(f"ERR: scratch DB already holds {existing} node revisions "
              f"(append-only); remove {storage.DB_PATH} manually to restart.",
              file=sys.stderr)
        return 1

    if args.basis_db is not None and not args.basis_db.is_file():
        print(f"ERR: basis DB not found: {args.basis_db}", file=sys.stderr)
        return 2
    fixture = args.basis_fixture or (REPO_ROOT / "tests" / "fixtures"
                                     / "nsm_axes_8.json")
    if not fixture.is_file():
        print(f"ERR: basis fixture not found: {fixture}", file=sys.stderr)
        return 2

    _, epoch = _copy_basis(str(db_path), args.basis_db, fixture)
    matrix = get_geodetic_matrix_db()
    axis_vectors = {axis_id: entry["vector"] for axis_id, entry in matrix.items()}
    theta_dyn = calibrate_critical_threshold(list(axis_vectors.values()))
    epsilon = resolve_epsilon_edge()
    print(f"[+] scratch DB: {storage.DB_PATH} | manifests={len(manifests)} "
          f"| epoch={epoch} | axes={len(axis_vectors)} "
          f"| theta_dyn={theta_dyn:.6f} | epsilon={epsilon}")
    print(f"[+] chunks to ingest: {len(chunks)}")

    dim_db = storage.get_current_dimension_db()
    telemetry: list[dict] = []
    labels_path = REPO_ROOT / ".data" / f"{stem}_labels.json"

    for index, (label, text) in enumerate(chunks, 1):
        native_vector = _encode_vector(text)
        dim_in = native_vector.size
        if dim_in > dim_db:
            raise ValueError(f"dim_in={dim_in} > dim_db={dim_db} (L6)")
        padded = (np.pad(native_vector, (0, dim_db - dim_in), mode="constant",
                         constant_values=0.0)
                  if dim_db > dim_in else native_vector)
        norm = np.linalg.norm(padded)
        unit_vector = padded / norm if norm > 0 else padded

        projections = {
            axis_id: float(np.dot(unit_vector, axis_vectors[axis_id]))
            for axis_id in axis_vectors
        }
        variance = float(np.var(list(projections.values())))
        dominant = max(axis_vectors,
                       key=lambda k: float(np.dot(unit_vector, axis_vectors[k])))
        gate = evaluate_gate_v01(list(projections.values()), True, theta_dyn)

        nid = node_id(index)
        with storage.get_db_connection() as conn:
            storage.insert_node_revision(
                nid,
                text,
                matrix[dominant]["symbol"],
                "pending_approval",
                variance,
                0,
                serialize_vector(unit_vector),
                json.dumps(projections),
                storage.active_epoch(),
                conn=conn,
            )
        telemetry.append({
            "node_id": nid,
            "label": label,
            "variance": variance,
            "dominant_axis": dominant,
            "gate_state": gate["state"],
        })

    n_edges = storage.persist_epsilon_edges(epsilon)

    labels_map = {item["node_id"]: item["label"] for item in telemetry}
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path.write_text(json.dumps(labels_map, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    summary = telemetry_summary([(t["node_id"], t["label"], t["variance"])
                                 for t in telemetry])
    consolidated = sum(1 for t in telemetry if t["gate_state"] == "consolidated")
    out_path = REPO_ROOT / ".data" / f"{stem}_telemetry.json"
    out_path.write_text(json.dumps(
        {"summary": summary, "theta_dyn": theta_dyn, "epsilon": epsilon,
         "n_edges_persisted": n_edges, "rows": telemetry},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[=] nodes: {summary['count']} | auto edges persisted: {n_edges}")
    print(f"[=] sigma^2 p50={summary['variance_p50']:.6f} "
          f"p95={summary['variance_p95']:.6f} "
          f"[{summary['variance_min']:.6f}, {summary['variance_max']:.6f}]")
    print(f"[=] dual-key gate (theta_dyn): {consolidated}/{summary['count']} "
          f"consolidated ({consolidated / summary['count']:.1%})")
    print(f"[+] labels map: {labels_path}")
    print(f"[+] telemetry JSON: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
