"""Light end-to-end pipeline test on a synthetic scratch manifold.

Runs the dynamic-audit chain (Otsu knee -> inter-part enrichment -> Fisher
battery) against a small in-memory-shaped SQLite DB, exercising the same
CLI entry points used in LEDGER seq 40 without any model or network.
"""
import json
import sqlite3

import numpy as np
import pytest

from tools.experiments.tooling.audit_axis_anisotropy import AXES

N_NODES = 12
PARTS = ["PART1_GOD_A", "PART2_MIND_B"]


def _cluster_vectors(rng):
    base_a = rng.standard_normal(384)
    base_b = rng.standard_normal(384)
    vectors = []
    for i in range(N_NODES):
        base = base_a if i % 2 == 0 else base_b
        noisy = base + rng.normal(scale=0.01, size=384)
        vectors.append(noisy / np.linalg.norm(noisy))
    return vectors


@pytest.fixture()
def scratch(tmp_path):
    rng = np.random.default_rng(42)
    vectors = _cluster_vectors(rng)
    db_path = tmp_path / "scratch.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE manifold_nodes (id TEXT PRIMARY KEY, text TEXT, "
        "vector_blob BLOB, projections_json TEXT, lifecycle_state TEXT, "
        "seq INTEGER)")
    labels = {}
    variance_rows = []
    for i, vec in enumerate(vectors):
        nid = f"NODE_{i + 1}"
        part = PARTS[i % len(PARTS)]
        labels[nid] = f"{part}_{i:02d}"
        projections = {f"AXIS_{k + 1}": float(rng.random())
                       for k in range(AXES)}
        conn.execute(
            "INSERT INTO manifold_nodes VALUES (?, ?, ?, ?, ?, 1)",
            (nid, f"chunk {i}", np.asarray(vec, dtype=np.float64).tobytes(),
             json.dumps(projections), "incubating"))
        variance_rows.append({"node_id": nid, "variance": 0.001 * (1 + i),
                              "dominant_axis": f"AXIS_{i % AXES + 1}",
                              "gate_state": "incubating"})
    conn.commit()
    conn.close()

    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(labels))
    telemetry_path = tmp_path / "telemetry.json"
    telemetry_path.write_text(json.dumps({
        "rows": variance_rows, "theta_dyn": 0.006}))
    return {"db": db_path, "labels": labels_path,
            "telemetry": telemetry_path}


def test_pipeline_knee_enrichment_fisher(scratch, tmp_path, monkeypatch):
    from tools.experiments.tooling import (
        epsilon_knee_audit, fisher_axis_part_test, inter_part_enrichment)

    knee_out = tmp_path / "knee.json"
    monkeypatch.setattr("sys.argv",
                        ["knee", "--db", str(scratch["db"]),
                         "--replicas", "10", "--json-out", str(knee_out)])
    epsilon_knee_audit.main()

    knee = json.loads(knee_out.read_text())
    assert knee["nodes"] == N_NODES
    assert 0.0 < knee["epsilon_star"] < 2.0
    assert knee["bridges_at_epsilon_star"] >= 0

    enrich_out = tmp_path / "enrichment.json"
    monkeypatch.setattr("sys.argv",
                        ["enrich", "--db", str(scratch["db"]),
                         "--labels", str(scratch["labels"]),
                         "--epsilon", repr(knee["epsilon_star"]),
                         "--json-out", str(enrich_out)])
    inter_part_enrichment.main()
    enrichment = json.loads(enrich_out.read_text())
    assert sum(enrichment["block_sizes"].values()) == N_NODES
    assert enrichment["total_edges"] >= 1

    fisher_out = tmp_path / "fisher.json"
    monkeypatch.setattr("sys.argv",
                        ["fisher", "--db", str(scratch["db"]),
                         "--labels", str(scratch["labels"]),
                         "--telemetry", str(scratch["telemetry"]),
                         "--unit", "all", "--replicas", "50",
                         "--blocks", "3",
                         "--json-out", str(fisher_out)])
    fisher_axis_part_test.main()
    fisher = json.loads(fisher_out.read_text())["all"]
    assert fisher["n_units"] == N_NODES
    assert 0.0 <= fisher["p_value"] <= 1.0
