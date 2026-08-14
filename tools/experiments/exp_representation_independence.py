#!/usr/bin/env python3
"""Representation Independence Experiment (issue #53).

Submits the SAME sequence of entities to the substrate under different
representation providers and verifies that the GOVERNANCE RULES are invariant
(ASSERT layer) while measuring the outcome coupling quantitatively (REPORT
layer).

Scenarios:
  A    SentenceTransformerProvider (all-MiniLM-L6-v2, 384D, offline)
  B    MockRepresentationProvider (isomorphic 384D, deterministic)
  C.1  SyntheticHeteroProvider(128D) -> zero-padding to 384D, full pipeline
  C.2  SyntheticHeteroProvider(512D) -> 422 fail-closed at the boundary

ASSERT (violation = exit 1):
  A. seq monotonicity: contiguous 1..N per id, append-only replay diff
  B. dual-key: EthicalKey=False -> incubating unconditionally
  C. allowed lifecycle states only
  D. fail-closed ingress: 400/415 with zero corrupt node rows
  E. NON-EMPTY, deterministic epsilon-edges (eps calibrated to a target
     pair density per provider; an empty edge set would make the
     determinism check and the edge-set Jaccard vacuous, so it is refused)

REPORT (never fails the run):
  kappa per provider/category, sigma^2 distribution, epsilon-edge count,
  edge-set Jaccard between scenarios (over non-empty calibrated sets).
  kappa spread IS the representation coupling index: it quantifies how each
  embedding space deforms consolidation geometry. Variation across providers
  is a MEASUREMENT of coupling, never a governance-rule failure.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

os.environ.setdefault("HF_HUB_OFFLINE", "1")
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.experiments._wp1_corpus import iter_corpus, validate_corpus  # noqa: E402
from traianus import app as main_module  # noqa: E402
from traianus import storage as storage  # noqa: E402
from traianus.representation.mock_provider import MockRepresentationProvider  # noqa: E402

ALLOWED_STATES = {"pending_approval", "incubating", "consolidated", "telemetry_error"}
EPSILON = 0.8
DEFAULT_EDGE_DENSITY = 0.05
DEFAULT_TOKEN = "exp-representation-independence"


class SyntheticHeteroProvider:
    """Seeded synthetic encoder of a configurable embedding width."""

    def __init__(self, dimension: int, seed: int = 0):
        self.dimension = dimension
        self._seed = seed

    def encode(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(self._seed + int.from_bytes(digest[:4], "little"))
        return rng.standard_normal(self.dimension).astype(np.float32)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        return np.stack([self.encode(t) for t in texts])


def _install_provider(provider) -> None:
    """Injects the provider into the app seam (lazy get_provider)."""
    main_module._provider = provider
    main_module.get_provider = lambda: provider


def _create_scenario_db(workdir: Path) -> Path:
    """Fresh ephemeral DB with the frozen realistic geodetic basis (384D)."""
    db_path = workdir / "scenario.db"
    storage.DB_PATH = str(db_path)
    storage.init_db()
    fixture = REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
    with sqlite3.connect(db_path) as conn:
        for entry in json.loads(fixture.read_text(encoding="utf-8")):
            vec = np.asarray(entry["vector"], dtype=np.float64)
            conn.execute(
                "INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob) "
                "VALUES (?, ?, ?, ?)",
                (entry["id"], entry["simbolo"], entry["tag"], vec.tobytes()),
            )
        conn.commit()
    return db_path


def _snapshot_nodes(db_path: Path) -> list[tuple]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT id, seq, text, toon_factor, lifecycle_state, action_potential, "
            "revision_milestone, vector_blob, projections_json, epoch_provenance "
            "FROM manifold_nodes ORDER BY id, seq"
        ).fetchall()


def calibrate_epsilon(vectors: list[np.ndarray],
                      target_density: float = DEFAULT_EDGE_DENSITY) -> float:
    """ε yielding a NON-EMPTY ε-edge set: the k-th smallest pairwise L2
    distance, k = max(1, int(target_density * n_pairs)). Deterministic.

    The default server epsilon (0.8) yields an EMPTY edge set on the 384D
    L2-normalized WP1 corpus, which makes edges_deterministic and the
    edge-set Jaccard vacuous (∅=∅); this calibration refuses to measure a
    degenerate graph.
    """
    normed = []
    for v in vectors:
        nrm = float(np.linalg.norm(v))
        if nrm > 0:
            normed.append(np.asarray(v) / nrm)
    n = len(normed)
    n_pairs = n * (n - 1) // 2
    if n_pairs == 0:
        return 0.0
    dists = sorted(
        float(np.linalg.norm(normed[i] - normed[j]))
        for i in range(n)
        for j in range(i + 1, n)
    )
    k = max(1, int(target_density * n_pairs))
    # Use the NEXT distance step (position k) as the threshold: the persisted
    # vector_blob is float64 while encode_batch is float32, so recomputed L2
    # distances drift ~1e-7 and the k-th closest pair would otherwise fall
    # OUTSIDE dist <= epsilon, making the calibrated set empty again.
    return dists[min(k, n_pairs - 1)]


def run_governance_scenario(provider, corpus, workdir: Path,
                            token: str = DEFAULT_TOKEN,
                            epsilon: float | None = None,
                            target_density: float = DEFAULT_EDGE_DENSITY) -> dict:
    """Runs the corpus through the full HTTP pipeline under one provider."""
    db_path = _create_scenario_db(workdir)
    _install_provider(provider)
    if epsilon is None:
        epsilon = calibrate_epsilon(
            [np.asarray(v) for v in provider.encode_batch([p for _, p in corpus])],
            target_density,
        )
    orig_epsilon = main_module.EPSILON_EDGE
    main_module.EPSILON_EDGE = epsilon
    os.environ["TRAIANUS_TOKEN"] = token
    auth = {"x-traianus-token": token}
    out = {"provider": type(provider).__name__,
           "dimension": getattr(provider, "dimension", None),
           "epsilon": epsilon}

    try:
        with TestClient(main_module.app) as client:
            out["probe_415"] = client.post(
                "/ingesta", content=b"{}",
                headers={**auth, "Content-Type": "application/json"},
            ).status_code
            out["probe_null"] = client.post(
                "/ingesta", content=b"a\x00b",
                headers={**auth, "Content-Type": "text/plain"},
            ).status_code

            category_by_node = {}
            accepted = 0
            for label, paragraph in corpus:
                res = client.post(
                    "/ingesta", content=paragraph.encode("utf-8"),
                    headers={**auth, "Content-Type": "text/plain"},
                )
                if res.status_code == 200:
                    accepted += 1
                    category_by_node[f"NODE_{res.json()['ingestion_id']}"] = label
            out["ingested"] = accepted

            nodes = client.get("/nodos", headers=auth).json().get("nodes", [])
            out["nodes"] = len(nodes)
            snapshot_ingest = _snapshot_nodes(db_path)

            state_counts = Counter()
            variances = defaultdict(list)
            consolidated_by_category = Counter()
            total_by_category = Counter()
            probe_dual_key_denied = None
            for n in nodes:
                label = category_by_node.get(n["id"])
                total_by_category[label] += 1
                resp = client.post(
                    f"/nodos/{n['id']}/consolidar",
                    json={"text": n["text"], "ethical_key": True},
                    headers=auth,
                )
                body = resp.json()
                state_counts[body["new_state"]] += 1
                if body["new_state"] == "consolidated":
                    consolidated_by_category[label] += 1
                variances[label].append(
                    body["dual_key_status"]["topological_key"]["variance"]
                )
                if probe_dual_key_denied is None:
                    denied = client.post(
                        f"/nodos/{n['id']}/consolidar",
                        json={"text": n["text"], "ethical_key": False},
                        headers=auth,
                    )
                    probe_dual_key_denied = denied.json()["new_state"]

            out["probe_dual_key_denied"] = probe_dual_key_denied
            out["state_counts"] = dict(state_counts)

            snapshot_consolidated = _snapshot_nodes(db_path)
            out["append_only_diff"] = all(
                old in snapshot_consolidated for old in snapshot_ingest
            )
            seqs = defaultdict(list)
            for row in snapshot_consolidated:
                seqs[row[0]].append(row[1])
            out["seq_monotonic"] = all(
                s == list(range(1, len(s) + 1)) for s in seqs.values()
            )
            out["allowed_states"] = {
                r[4] for r in snapshot_consolidated
            } <= ALLOWED_STATES

            relations = client.get("/relations", headers=auth).json()
            auto_ids = sorted(
                r["id"] for r in relations if r["id"].startswith("auto-edge-")
            )
            out["auto_edge_ids"] = auto_ids
            out["edge_count"] = len(auto_ids)
            n = len(nodes)
            out["edge_density"] = (
                len(auto_ids) / (n * (n - 1) / 2) if n > 1 else 0.0
            )

            rebuilt = storage.rebuild_epsilon_edges(epsilon)
            rebuilt_ids = sorted(
                f"auto-edge-{e['source']}-{e['target']}" for e in rebuilt
            )
            out["edges_deterministic"] = auto_ids == rebuilt_ids

            kappa, sigma2 = {}, {}
            for label in sorted(total_by_category):
                total = total_by_category[label]
                kappa[label] = (
                    consolidated_by_category[label] / total if total else 0.0
                )
                v = variances[label]
                sigma2[label] = (
                    {"mean": float(np.mean(v)), "var": float(np.var(v))}
                    if v else None
                )
            out["kappa"] = kappa
            out["sigma2"] = sigma2
            out["kappa_overall"] = (
                sum(consolidated_by_category.values()) / len(nodes) if nodes else 0.0
            )
        return out
    finally:
        main_module.EPSILON_EDGE = orig_epsilon


def run_rejection_scenario(workdir: Path, token: str = DEFAULT_TOKEN) -> dict:
    """C.2: a 512D provider must be fail-closed with zero node side effects."""
    db_path = _create_scenario_db(workdir)
    _install_provider(SyntheticHeteroProvider(512, seed=2026))
    os.environ["TRAIANUS_TOKEN"] = token
    auth = {"x-traianus-token": token}
    out = {"provider": "c2-hetero-512", "dimension": 512}
    rng = np.random.default_rng(2026)
    vec = rng.standard_normal(512)
    vec = (vec / np.linalg.norm(vec)).tolist()

    with TestClient(main_module.app) as client:
        res = client.post("/ingesta/vector", json={"vector": vec}, headers=auth)
        out["vector_422"] = res.status_code
        text = client.post(
            "/ingesta", content="512d note".encode("utf-8"),
            headers={**auth, "Content-Type": "text/plain"},
        )
        out["text_accepted"] = text.status_code

    with sqlite3.connect(db_path) as conn:
        out["node_rows_written"] = conn.execute(
            "SELECT COUNT(*) FROM manifold_nodes WHERE id LIKE 'NODE_%'"
        ).fetchone()[0]
        out["telemetry_error_rows"] = conn.execute(
            "SELECT COUNT(*) FROM manifold_nodes WHERE lifecycle_state = 'telemetry_error'"
        ).fetchone()[0]
        seqs = defaultdict(list)
        for row in conn.execute("SELECT id, seq FROM manifold_nodes ORDER BY id, seq"):
            seqs[row[0]].append(row[1])
        out["seq_monotonic"] = all(
            s == list(range(1, len(s) + 1)) for s in seqs.values()
        )
    return out


def assert_invariants(metrics: dict) -> bool:
    """ASSERT layer: governance rules must hold; violation raises AssertionError."""
    checks = {
        "seq_monotonic": metrics.get("seq_monotonic"),
        "append_only_diff": metrics.get("append_only_diff"),
        "allowed_states": metrics.get("allowed_states"),
        "dual_key_denied_incubating": metrics.get("probe_dual_key_denied") == "incubating",
        "non_vacuous_edges": metrics.get("edge_count", 0) > 0,
        "edges_deterministic": metrics.get("edges_deterministic"),
        "ingress_415": metrics.get("probe_415") == 415,
        "ingress_null_400": metrics.get("probe_null") == 400,
    }
    for name, ok in checks.items():
        if not ok:
            raise AssertionError(f"governance invariant violated: {name}")
    return True


def assert_rejection_invariants(metrics: dict) -> bool:
    checks = {
        "vector_422": metrics.get("vector_422") == 422,
        "node_rows_written": metrics.get("node_rows_written") == 0,
        "text_accepted": metrics.get("text_accepted") == 200,
        "telemetry_error_rows": metrics.get("telemetry_error_rows") == 1,
        "seq_monotonic": metrics.get("seq_monotonic"),
    }
    for name, ok in checks.items():
        if not ok:
            raise AssertionError(f"rejection invariant violated: {name}")
    return True


def _jaccard(x: list, y: list) -> float:
    sx, sy = set(x), set(y)
    return len(sx & sy) / len(sx | sy) if (sx or sy) else 1.0


def compute_coupling_report(results: dict) -> dict:
    """REPORT layer: outcome coupling metrics (never fails the run)."""
    report = {}
    for name, m in results.items():
        if "kappa_overall" in m:
            report[name] = {
                "kappa_overall": m["kappa_overall"],
                "kappa": m.get("kappa"),
                "edge_count": m.get("edge_count"),
                "edge_density": round(m.get("edge_density", 0.0), 4),
                "sigma2_mean": {
                    k: round(v["mean"], 6) for k, v in (m.get("sigma2") or {}).items()
                },
            }
        else:
            report[name] = {k: m[k] for k in ("vector_422", "node_rows_written",
                                              "telemetry_error_rows")}
    gov = [name for name, m in results.items() if "auto_edge_ids" in m]
    report["edge_jaccard"] = {}
    for i, a in enumerate(gov):
        for b in gov[i + 1:]:
            report["edge_jaccard"][f"{a}<->{b}"] = _jaccard(
                results[a]["auto_edge_ids"], results[b]["auto_edge_ids"]
            )
    rates = {n: m.get("kappa_overall") for n, m in results.items() if "kappa_overall" in m}
    report["rate_spread"] = max(rates.values()) - min(rates.values()) if rates else 0.0
    # kappa spread is the representation coupling index (REPORT): it measures
    # how each embedding space deforms consolidation geometry. It is NOT a
    # governance-rule failure; the ASSERT layer covers the rules only.
    report["coupling_index"] = report["rate_spread"]
    return report


GOVERNANCE_SCENARIOS = {
    "a": lambda seed: _build_model_provider(),
    "b": lambda seed: MockRepresentationProvider(),
    "c1": lambda seed: SyntheticHeteroProvider(128, seed=seed),
}


def _build_model_provider():
    from traianus.representation.sentence_transformer import SentenceTransformerProvider
    return SentenceTransformerProvider()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--providers", default="b,c1,c2",
        help="comma list of a,b,c1,c2 or 'all' (a requires the cached offline model)",
    )
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--limit", type=int, default=0,
                        help="cap the corpus to N notes (0 = full WP1 corpus)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    selected = list(GOVERNANCE_SCENARIOS) + ["c2"] if args.providers == "all" \
        else [p.strip() for p in args.providers.split(",")]
    validate_corpus()
    corpus = list(iter_corpus())
    if args.limit and args.limit < len(corpus):
        corpus = corpus[:args.limit]

    results, failures = {}, []
    for name in selected:
        if name in GOVERNANCE_SCENARIOS:
            with tempfile.TemporaryDirectory() as td:
                metrics = run_governance_scenario(
                    GOVERNANCE_SCENARIOS[name](args.seed), corpus, Path(td)
                )
            results[name] = metrics
            try:
                assert_invariants(metrics)
            except AssertionError as exc:
                failures.append((name, str(exc)))
        elif name == "c2":
            with tempfile.TemporaryDirectory() as td:
                metrics = run_rejection_scenario(Path(td))
            results[name] = metrics
            try:
                assert_rejection_invariants(metrics)
            except AssertionError as exc:
                failures.append((name, str(exc)))
        else:
            print(f"unknown provider scenario: {name}")
            return 2

    report = compute_coupling_report(results)
    print("=== REPRESENTATION INDEPENDENCE EXPERIMENT ===")
    for name, m in results.items():
        if "kappa_overall" in m:
            print(f"[{name}] provider={m['provider']} dim={m['dimension']} "
                  f"nodes={m['nodes']} kappa={m['kappa_overall']:.3f} "
                  f"eps={m.get('epsilon', EPSILON):.4f} "
                  f"edges={m['edge_count']} states={m['state_counts']}")
        else:
            print(f"[{name}] provider={m['provider']} vector_422={m['vector_422']} "
                  f"node_rows_written={m['node_rows_written']} "
                  f"telemetry_error_rows={m['telemetry_error_rows']}")
    print(f"edge_jaccard={report['edge_jaccard']} "
          f"rate_spread={report['rate_spread']:.3f}")
    print("REPORT -- kappa spread is the REPRESENTATION COUPLING index: it "
          "quantifies how each embedding space deforms consolidation geometry. "
          "Governance RULES (ASSERT layer) are invariant and independent of kappa.")

    if failures:
        print("RED -- governance ASSERT violated:")
        for name, msg in failures:
            print(f"  [{name}] {msg}")
        return 1
    print("GREEN -- governance rules invariant across every scenario")
    if args.json:
        print(json.dumps({"results": results, "report": report}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
