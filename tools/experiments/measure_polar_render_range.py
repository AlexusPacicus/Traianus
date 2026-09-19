"""Measure how much of the renderer's coordinate range the polar spatial
observables occupy, over the frozen Spinoza corpora, raw and calibrated.

The x/y channels are a direct readout of the PolarProjector decomposition, so a
node's position is local and drift-free by construction — but mathematical
separation is not visual separation. This quantifies the gap the per-epoch
SpatialCalibration has to close, and checks it actually closes it.

Read-only against .data/part*.db (nodes and their own active geodetic basis).
Offline: numpy + traianus only. Console report, no data files (AGENTS 1.2).
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments.tooling._common import load_nodes  # noqa: E402
from traianus.geometry.spatial_observables import (  # noqa: E402
    EPOCH_PROVENANCE,
    derive_spatial_observables,
    fit_spatial_calibration,
)

POSITION_CHANNELS = ("x", "y")


def load_geodetic_matrix(db_path: Path) -> dict[str, np.ndarray]:
    """Active geodetic basis of one corpus DB, keyed by axis id."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT id, vector_blob FROM geodesic_axes "
            "WHERE epoch_provenance = ? ORDER BY id",
            (EPOCH_PROVENANCE,),
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < 3:
        raise SystemExit(f"ERR: need >= 3 geodetic axes in {db_path}, got {len(rows)}")
    return {r[0]: np.frombuffer(r[1], dtype=np.float64) for r in rows}


def describe(name: str, values: np.ndarray, full_range: float) -> None:
    lo, hi = float(values.min()), float(values.max())
    span = hi - lo
    p01, p50, p99 = np.percentile(values, [1, 50, 99])
    print(
        f"  {name:<11} min={lo:+.5f} p01={p01:+.5f} p50={p50:+.5f} "
        f"p99={p99:+.5f} max={hi:+.5f} sd={values.std():.5f} "
        f"span={span:.5f} occupancy={100.0 * span / full_range:6.2f}%"
    )


def report_channels(label: str, channels: dict[str, list[float]]) -> None:
    print(f"\n== {label} ==")
    describe("x (lambda)", np.asarray(channels["x"]), 2.0)
    describe("y (anchor)", np.asarray(channels["y"]), 2.0)
    describe("h (esc)", np.asarray(channels["h"]), 1.0)
    describe("l (density)", np.asarray(channels["l"]), 1.0)


def report_coupling(pooled: dict[str, list[float]]) -> None:
    """Are the two position channels independent, or one in disguise?

    h (the escape distance) is included to exhibit the analytic redundancy
    d_esc^2 = 1 - y^2 - lambda^2 ||v_dipole||^2, which is why it is not an axis.
    """
    names = (*POSITION_CHANNELS, "h")
    M = np.vstack([np.asarray(pooled[k]) for k in names])
    corr = np.corrcoef(M)
    print("\n-> Pearson correlation (position channels + escape distance):")
    for i, name in enumerate(names):
        print(f"     {name}: " + "  ".join(f"{corr[i][j]:+.4f}" for j in range(len(names))))


def report_calibrated(pooled: dict[str, list[float]]) -> None:
    """Occupancy once the frozen per-epoch affine map is applied."""
    raw = list(zip(pooled["x"], pooled["y"], strict=True))
    cal = fit_spatial_calibration(raw, EPOCH_PROVENANCE)
    mapped = [cal.apply(x, y) for x, y in raw]
    xs = np.asarray([p[0] for p in mapped])
    ys = np.asarray([p[1] for p in mapped])
    print(
        f"\n-> calibration fitted for {EPOCH_PROVENANCE}: "
        f"mu=({cal.mu_x:+.5f}, {cal.mu_y:+.5f}) "
        f"sigma=({cal.sigma_x:.5f}, {cal.sigma_y:.5f}) k={cal.k_sigma:.1f}"
    )
    describe("x calib", xs, 2.0)
    describe("y calib", ys, 2.0)
    area = (xs.max() - xs.min()) * (ys.max() - ys.min())
    print(f"-> calibrated x-y bounding box covers {100.0 * area / 4.0:.2f}% of the viewport")
    print(f"-> nodes clipped at the box edge: {int(np.sum((np.abs(xs) >= 1.0) | (np.abs(ys) >= 1.0)))} / {len(xs)}")


def main() -> None:
    dbs = sorted((REPO_ROOT / ".data").glob("part*.db"))
    if not dbs:
        raise SystemExit("ERR: no .data/part*.db corpora found")

    pooled: dict[str, list[float]] = {k: [] for k in ("x", "y", "z", "l", "c", "h")}

    for db in dbs:
        basis = load_geodetic_matrix(db)
        _ids, _texts, X = load_nodes(db)
        channels: dict[str, list[float]] = {k: [] for k in pooled}
        for v in X:
            obs = derive_spatial_observables(v, basis)
            for k in channels:
                channels[k].append(obs[k])
                pooled[k].append(obs[k])
        report_channels(f"{db.name}  (n={len(X)}, k={len(basis)} axes)", channels)

    report_channels(f"POOLED RAW (n={len(pooled['x'])})", pooled)

    xs = np.asarray(pooled["x"])
    ys = np.asarray(pooled["y"])
    area = (xs.max() - xs.min()) * (ys.max() - ys.min())
    print(f"\n-> raw x-y bounding box covers {100.0 * area / 4.0:.3f}% of the viewport")
    report_coupling(pooled)
    report_calibrated(pooled)


if __name__ == "__main__":
    main()
