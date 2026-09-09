"""Scale-stress the Polar Projector against n = 2,221 real Spinoza embeddings
scaled to ~25k nodes via deterministic drift replication (manuscript §1.1).

Demonstrates empirically that the projector is O(1) with respect to corpus size
N (each project() is O(d), d=384) at the 25k collapse point of O(N^2) force
simulations, and verifies SQLite WAL persistence at that scale.

The control-plane scaling is the ejecta of the paper's claim: read latencies
stay flat as N grows, while a naive O(N^2) force pass explodes.

Read-only on the frozen Spinoza vectors (.data/part*.db, committed manifests).
Offline: numpy + traianus only. Emits a console report, no data files.
"""

import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.polar_fixtures import random_unit_vector
from traianus.geometry.polar_projector import PolarProjector

D = 384
DRIFT_SCALE = 0.02  # perturbation radius for drift-replicated variants
VARIANTS_PER_BASE = 12  # 2221 * 12 = 26652 >= 25000
TARGET = 25000
SCALE_POINTS = (2221, 5000, 10000, 20000, TARGET)
BLOB_BYTES = D * 8  # 3072 B float64


def load_spinoza_vectors() -> np.ndarray:
    vectors = []
    for db in sorted((REPO_ROOT / ".data").glob("part*.db")):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT vector_blob FROM manifold_nodes "
                "WHERE seq = (SELECT MAX(seq) FROM manifold_nodes m2 "
                "WHERE m2.id = manifold_nodes.id)"
            ).fetchall()
        finally:
            con.close()
        for (blob,) in rows:
            vectors.append(np.frombuffer(blob, dtype=np.float64))
    return np.asarray(vectors, dtype=np.float64)


def replicate_with_drift(base: np.ndarray, variants: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(base)
    total = variants * n
    out = np.empty((total, D), dtype=np.float64)
    for i in range(variants):
        noise = rng.normal(scale=DRIFT_SCALE, size=(n, D)).astype(np.float64)
        v = base + noise
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        out[i * n : (i + 1) * n] = v
    return out


def projector_latency(vectors: np.ndarray, anchor: np.ndarray, c_a: np.ndarray, c_b: np.ndarray) -> tuple[float, float]:
    projector = PolarProjector()
    m = len(vectors)
    d_escs = np.empty(m, dtype=np.float64)
    starts = np.empty(m, dtype=np.float64)
    ends = np.empty(m, dtype=np.float64)
    for i in range(m):
        t0 = time.perf_counter()
        _, _, de = projector.project(vectors[i], anchor, c_a, c_b, i)
        t1 = time.perf_counter()
        starts[i] = t0
        ends[i] = t1
        d_escs[i] = de
    lat = ends - starts
    lat_sorted = np.sort(lat)
    p95 = float(lat_sorted[int(0.95 * m)])
    return float(lat.mean()), p95


def force_pass_quadratic(vectors: np.ndarray) -> float:
    """One O(N^2) pairwise repulsion+gravity pass (d3-force style).

    Inherently O(N^2 * d); measured only at feasible N (see FORCE_MEASURE_N),
    then extrapolated to TARGET via the quadratic scaling law t ~ a*N^2.
    """
    m = len(vectors)
    t0 = time.perf_counter()
    for i in range(m):
        d = vectors - vectors[i]  # (m, D)
        dist = np.linalg.norm(d, axis=1)
        dist[dist < 1e-6] = 1e-6
        _ = np.sum(d / dist[:, None] ** 3, axis=0)
    t1 = time.perf_counter()
    return t1 - t0


FORCE_MEASURE_N = (1000, 2221, 4000)


def force_scaling_law_to_25k(full: np.ndarray) -> float:
    """Measure t(N) at feasible sizes and extrapolate T(N) ~ a*N^2 to 25000."""
    times = []
    for n in FORCE_MEASURE_N:
        t = force_pass_quadratic(full[:n])
        times.append((n, t))
        print(f"{n:>6}{t:>15.3f}", flush=True)
    ns = np.asarray([x[0] for x in times], dtype=np.float64)
    ts = np.asarray([x[1] for x in times], dtype=np.float64)
    a = float(np.sum(ns ** 2 * ts) / np.sum(ns ** 4))  # least-squares slope t=a*N^2
    t25 = a * TARGET ** 2
    print(f"  └─ fit: t(N) = {a:.3e} * N^2"
          f"  =>  t({TARGET}) = {t25:.1f} s = {t25 / 60:.1f} min")
    return t25


def wal_ingest_25k(vectors: np.ndarray) -> dict:
    from traianus.storage.sqlite_engine import SQLiteEngine

    tmp = REPO_ROOT / ".data" / "_scale_stress_test.db"
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(tmp) + suffix)
        if p.exists():
            p.unlink()
    engine = SQLiteEngine(str(tmp))
    try:
        t0 = time.perf_counter()
        with engine._transaction() as conn:
            for i, v in enumerate(vectors):
                engine.insert_data_plane(f"n_{i}", v, conn=conn)
        t_ingest = time.perf_counter() - t0

        t0 = time.perf_counter()
        with engine._transaction() as conn:
            for i in range(len(vectors)):
                conn.execute(
                    "INSERT INTO control_plane (node_id, centroid_id, version) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(node_id) DO UPDATE SET version = excluded.version",
                    (f"n_{i}", i % 10, 1),
                )
        t_reindex = time.perf_counter() - t0

        stop = threading.Event()
        writer = threading.Thread(
            target=_background_writer, args=(engine, len(vectors), stop), daemon=True
        )
        hot_baseline = _run_hot_reads(engine, len(vectors), writer=None)
        hot_during = _run_hot_reads(engine, len(vectors), writer=writer)
    finally:
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(tmp) + suffix)
            if p.exists():
                p.unlink()
    return {
        "n": len(vectors),
        "ingest_ms": t_ingest * 1000.0,
        "reindex_ms": t_reindex * 1000.0,
        "blob_bytes": BLOB_BYTES,
        "total_mb": len(vectors) * BLOB_BYTES / 1e6,
        "hot_baseline": hot_baseline,
        "hot_during_write": hot_during,
    }


N_HOT_READERS = 191  # §5: 191 simultaneous hot reads during destructive re-index
BUSY_ERR = "database is locked"


def _run_hot_reads(engine, n_nodes: int, writer: threading.Thread | None) -> dict:
    """One hot-read pass; counts real WAL lock events (SQLITE_BUSY only)."""
    latencies: list[float] = []
    lock_events: list[str] = []
    stop = threading.Event()

    def hot_reader(i: int) -> None:
        conn = engine._connect()
        try:
            conn.execute(
                "SELECT vector_blob, dimension FROM data_plane "
                "WHERE node_id = ? ORDER BY seq DESC LIMIT 1",
                (f"n_{i}",),
            ).fetchone()
            conn.execute(
                "SELECT centroid_id, version FROM control_plane WHERE node_id = ?",
                (f"n_{i}",),
            ).fetchone()
            t0 = time.perf_counter()
            _ = conn.execute(
                "SELECT vector_blob, dimension FROM data_plane "
                "WHERE node_id = ? ORDER BY seq DESC LIMIT 1",
                (f"n_{i}",),
            ).fetchone()
            _ = conn.execute(
                "SELECT centroid_id, version FROM control_plane WHERE node_id = ?",
                (f"n_{i}",),
            ).fetchone()
            dt = time.perf_counter() - t0
        except sqlite3.OperationalError as exc:
            if BUSY_ERR in str(exc):
                lock_events.append(repr(exc))
            dt = time.perf_counter() - t0
        finally:
            conn.close()
        latencies.append(dt)

    if writer is not None:
        writer.start()
    n = min(N_HOT_READERS, n_nodes)
    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(hot_reader, range(n)))
    if writer is not None:
        stop.set()
        writer.join(timeout=10.0)

    latencies.sort()
    return {
        "n_readers": n,
        "mean_us": float(np.mean(latencies)) * 1e6,
        "max_us": latencies[-1] * 1e6,
        "locks": len(lock_events),
    }


def _background_writer(engine, n_nodes: int, stop: threading.Event) -> None:
    version = 2
    while not stop.is_set():
        with engine._transaction() as conn:
            for i in range(n_nodes):
                conn.execute(
                    "UPDATE control_plane SET version = ? WHERE node_id = ?",
                    (version, f"n_{i}"),
                )
        version += 1


def main() -> int:
    print(f"Polar Projector O(1) scale-stress (d={D}, target ~{TARGET} nodes via drift replication)")

    base = load_spinoza_vectors()
    print(f"[load] real Spinoza vectors: {len(base)}")

    full = replicate_with_drift(base, VARIANTS_PER_BASE, seed=42)[:TARGET]
    print(f"[replicate] ~{len(full)} vectors (drift scale={DRIFT_SCALE}, seed=42)")

    anchor = random_unit_vector(D, 1)
    c_a = random_unit_vector(D, 2)
    c_b = random_unit_vector(D, 3)

    print("\n=== Control plane: projector latency vs N (expect flat / O(1)) ===")
    print(f"{'N':>6}{'mean_lat(us)':>14}{'p95_lat(us)':>13}")
    for n in SCALE_POINTS:
        vecs = full[:n]
        mean_us, p95_us = projector_latency(vecs, anchor, c_a, c_b)
        print(f"{n:>6}{mean_us * 1e6:>14.2f}{p95_us * 1e6:>13.2f}")

    print("\n=== Contrapunto: O(N^2) force pass (collapse the paper describes) ===")
    print(f"measured at N in {FORCE_MEASURE_N}, extrapolated to {TARGET}:")
    print(f"{'N':>6}{'force_pass(s)':>15}")
    force_scaling_law_to_25k(full)

    print("\n=== Persistence: SQLite WAL at 25k ===")
    metric = wal_ingest_25k(full)
    base = metric["hot_baseline"]
    during = metric["hot_during_write"]
    print(f"{'n':<8}{'ingest(ms)':<12}{'reindex(ms)':<14}{'total(MB)':<12}{'blob(B)'}")
    print(f"{metric['n']:<8}{metric['ingest_ms']:<12.2f}{metric['reindex_ms']:<14.2f}"
          f"{metric['total_mb']:<12.1f}{metric['blob_bytes']}")
    print("\nhot reads (191 concurrent, warm cache):")
    print(f"{'phase':<12}{'n':<6}{'mean(us)':<11}{'max(us)':<11}{'lock events'}")
    print(f"{'baseline':<12}{base['n_readers']:<6}{base['mean_us']:<11.2f}"
          f"{base['max_us']:<11.2f}{base['locks']}")
    print(f"{'during write':<12}{during['n_readers']:<6}{during['mean_us']:<11.2f}"
          f"{during['max_us']:<11.2f}{during['locks']}")

    print("\nVerdict: if projector latencies stay flat as N grows while the O(N^2) "
          "pass diverges, the O(1)-vs-N claim holds at the 25k collapse point.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
