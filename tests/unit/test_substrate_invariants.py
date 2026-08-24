"""Substrate invariant hardening suite (issue #52).

Two invariant families independent of vector content and of the neural model:

* A. WAL append-only: operational replay/diff over a full mutation sequence,
  contiguous seq under concurrency, journal_mode=wal, and a static scan for
  destructive SQL against the node log and geodetic axes.
* B. Dual-key C1 gate: exhaustive truth-table property over seeded synthetic
  spectra, calibration determinism with self-projection excluded, and the
  provider-agnostic /ingesta/vector integration path.
* C. Zero-Trust ingress byte boundary cases live in tests/test_security.py.
"""
import re
import sqlite3
import threading
from pathlib import Path

import numpy as np
import pytest

import traianus.app as main
import traianus.storage as storage
from traianus.app import serialize_vector
from traianus.core import calibrate_critical_threshold, evaluate_gate_v01

REPO_ROOT = Path(__file__).resolve().parent.parent
DESTRUCTIVE_RE = re.compile(
    r"(UPDATE|REPLACE|DELETE)\s+(manifold_nodes|manifold_edges|geodesic_axes)\b",
    re.IGNORECASE,
)


def _snapshot_nodes(db_path):
    """Full (id, seq, ...) rows of the node log, ordered and immutable."""
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT id, seq, text, toon_factor, lifecycle_state, action_potential, "
            "revision_milestone, vector_blob, projections_json, epoch_provenance "
            "FROM manifold_nodes ORDER BY id, seq"
        ).fetchall()


class TestWALAppendOnly:
    def test_operational_replay_is_append_only(self, client, ingesta, auth_headers, isolate_db):
        """Invariant A: every mutation only appends revisions with increasing seq."""
        res_a = ingesta("Alpha")
        res_b = ingesta("Beta")
        ingesta("Gamma")
        snapshots = [
            _snapshot_nodes(isolate_db),
            _snapshot_nodes(isolate_db),
        ]
        alpha_id = f"NODE_{res_a.json()['ingestion_id']}"
        beta_id = f"NODE_{res_b.json()['ingestion_id']}"
        assert client.post(
            f"/nodos/{alpha_id}/consolidar",
            json={"text": "Alpha", "ethical_key": True},
            headers=auth_headers,
        ).status_code == 200
        snapshots.append(_snapshot_nodes(isolate_db))
        assert client.post(
            "/relations",
            json={"source": alpha_id, "target": beta_id, "state": "manual"},
            headers=auth_headers,
        ).status_code == 200
        snapshots.append(_snapshot_nodes(isolate_db))

        for prev, curr in zip(snapshots, snapshots[1:]):
            for old_row in prev:
                assert old_row in curr, f"node row mutated or removed: {old_row}"
        seqs = {}
        for row in _snapshot_nodes(isolate_db):
            seqs.setdefault(row[0], []).append(row[1])
        for node_id, seq_list in seqs.items():
            assert seq_list == list(range(1, len(seq_list) + 1)), \
                f"seq not contiguous for {node_id}: {seq_list}"
        assert seqs[alpha_id] == [1, 2]

    def test_concurrent_inserts_contiguous_seq_per_id(self, isolate_db):
        """Invariant A: N concurrent revisions of one node yield seq 1..N."""
        n_threads = 8
        barrier = threading.Barrier(n_threads)
        vector_blob = serialize_vector(np.zeros(384, dtype=np.float64))

        def worker(_i):
            barrier.wait()
            for _attempt in range(64):
                try:
                    storage.insert_node_revision(
                        "CONCURRENT_NODE", "concurrent", "\u25b2", "incubating", 0.1, 0,
                        vector_blob, "{}", "PROSTHETIC_NSM_V1",
                    )
                    return
                except sqlite3.IntegrityError:
                    continue
            raise RuntimeError("worker exhausted insert retries")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with sqlite3.connect(isolate_db) as conn:
            rows = conn.execute(
                "SELECT seq, text, lifecycle_state FROM manifold_nodes "
                "WHERE id = 'CONCURRENT_NODE' ORDER BY seq"
            ).fetchall()
        assert [r[0] for r in rows] == list(range(1, n_threads + 1))
        assert all(r[1] == "concurrent" and r[2] == "incubating" for r in rows)

    def test_journal_mode_is_wal_after_operations(self, isolate_db):
        """Invariant A: connections run under WAL journal mode."""
        with sqlite3.connect(isolate_db) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_no_destructive_sql_against_node_log_or_axes(self):
        """Invariant A: static scan for UPDATE/REPLACE/DELETE on node log/axes."""
        offenders = []
        for py in (REPO_ROOT / "traianus").rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for match in DESTRUCTIVE_RE.finditer(text):
                offenders.append(f"{py.relative_to(REPO_ROOT)}:{match.group(0)}")
        assert offenders == [], f"destructive SQL against node log/axes: {offenders}"


class TestDualKeyC1Gate:
    def test_dual_key_truth_table_over_synthetic_spectra(self):
        """Invariant B: Consolidated <=> (var >= theta) AND (EthicalKey)."""
        rng = np.random.default_rng(20260814)
        thresholds = [0.0, 0.001, 0.01, 0.1, 0.5]
        for _ in range(300):
            spectrum = rng.standard_normal(8).tolist()
            variance = float(np.var(spectrum))
            for threshold in thresholds:
                denied = evaluate_gate_v01(spectrum, ethical_key=False, threshold=threshold)
                assert denied["state"] == "incubating"
                assert denied["topological_key"]["passed"] == (variance >= threshold)
                granted = evaluate_gate_v01(spectrum, ethical_key=True, threshold=threshold)
                expected = "consolidated" if variance >= threshold else "incubating"
                assert granted["state"] == expected

    def test_calibration_deterministic_and_excludes_self_projection(self):
        """Invariant B: threshold is a pure function of the axes, cross-only."""
        rng = np.random.default_rng(42)
        raw = rng.standard_normal((8, 384))
        axes = [v / np.linalg.norm(v) for v in raw]
        first = calibrate_critical_threshold(axes)
        second = calibrate_critical_threshold(axes)
        assert first == pytest.approx(second)
        cross_variances = []
        for i in range(len(axes)):
            projections = [
                float(np.dot(axes[i], axes[j])) for j in range(len(axes)) if j != i
            ]
            cross_variances.append(float(np.var(projections)))
        assert first == pytest.approx(float(np.mean(cross_variances)))

    def test_ingesta_vector_requires_ethical_key(self, client, auth_headers, isolate_db):
        """Invariant B: /ingesta/vector + consolidate needs BOTH keys."""
        rng = np.random.default_rng(7)
        vec = rng.standard_normal(384)
        vec = (vec / np.linalg.norm(vec)).tolist()
        res = client.post("/ingesta/vector", json={"vector": vec}, headers=auth_headers)
        assert res.status_code == 201
        body = res.json()
        node_id = body["node_id"]
        assert body["lifecycle_state"] == "incubating"
        assert body["dual_key_status"]["topological_key"]["passed"] is True
        denied = client.post(
            f"/nodos/{node_id}/consolidar",
            json={"text": "x", "ethical_key": False},
            headers=auth_headers,
        )
        assert denied.status_code == 200
        assert denied.json()["new_state"] == "incubating"
        granted = client.post(
            f"/nodos/{node_id}/consolidar",
            json={"text": "x", "ethical_key": True},
            headers=auth_headers,
        )
        assert granted.status_code == 200
        assert granted.json()["new_state"] == "consolidated"
