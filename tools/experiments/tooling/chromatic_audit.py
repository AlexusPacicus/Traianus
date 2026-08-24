#!/usr/bin/env python
"""Chromatic audit of the Spinoza Part II manifold for Ulpia's effective 5D.

Evaluates how independent chromatic channels (R, G, B) rescue significant
load collapsed onto the 2D screen. Read-only: never mutates the substrate.

Pipeline (all offline, committed tooling only):
1. effective 5D projection: X,Y = PC1,PC2 (spatial); R,G,B = PC3..PC5
   weighted by singular values (variance-faithful), min-max scaled to [0,1].
2. collision detection & rescue: pairs close in 2D (<= p5 of 2D distances)
   but far in 384D (>= p95) are "collisions"; pairs with identical vectors
   are stylistic duplicates (artifacts, not rescuable).
3. discernibility: fraction of collisions with chromatic separation
   delta_rgb > 0.15 after channel scaling.
4. Sammon stress of the 2D plane vs the 5D space against the true 384-D
   metric -> decompression gain of the chromatic channels.
5. falsifiable ontological alignment (Spinoza domains):
   soma = P24-P31, duration = DEF_05, potestas = P37-P49; point-biserial
   correlation between zone membership and per-channel intensity with
   confirmed / neutral / refuted verdicts.

Output: .data/spinoza_part2_chromatic.json
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB = REPO_ROOT / ".data" / "spinoza_part2.db"
DEFAULT_LABELS = REPO_ROOT / ".data" / "spinoza_part2_labels.json"
DEFAULT_OUT = REPO_ROOT / ".data" / "spinoza_part2_chromatic.json"

RGB_DISCERNIBLE_THRESHOLD = 0.15


def effective_5d(X) -> np.ndarray:
    """Variance-faithful 5D layout: x,y spatial + r,g,b in [0,1].

    Reuses traianus.geometry.svd_reduce(k=5): columns are U*S with the
    canonical sign convention; RGB channels are min-max normalized.
    """

    from traianus.geometry.observables import svd_reduce

    coords, _ = svd_reduce(X, k=5)
    out = np.zeros((coords.shape[0], 6))
    out[:, 0:2] = coords[:, 0:2]
    rgb = coords[:, 2:5]
    span = rgb.max(axis=0) - rgb.min(axis=0)
    span[span == 0] = 1.0
    out[:, 2:5] = (rgb - rgb.min(axis=0)) / span
    return out


def pairwise_dists(P) -> np.ndarray:
    return np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)


def _offdiag_percentile(D: np.ndarray, pct: float) -> float:
    vals = D[np.triu_indices(D.shape[0], k=1)]
    return float(np.percentile(vals, pct))


def find_collisions(pts2d, pts384, close_pct: float = 5.0, far_pct: float = 95.0):
    """Returns (collisions, duplicates).

    collisions: [(i, j, d2d, d384)] with d2d <= p_close(2D distances) and
                d384 >= p_far(384-D distances), sorted by d2d ascending.
    duplicates: [(i, j, d384)] with numerically identical vectors.
    """
    D2 = pairwise_dists(pts2d)
    D384 = pairwise_dists(pts384)
    thr_close = _offdiag_percentile(D2, close_pct)
    thr_far = _offdiag_percentile(D384, far_pct)
    iu, ju = np.triu_indices(D2.shape[0], k=1)
    collisions, duplicates = [], []
    for a, b in zip(iu, ju):
        d2d, dh = float(D2[a, b]), float(D384[a, b])
        if dh < 1e-9:
            duplicates.append((int(a), int(b), dh))
        elif d2d <= thr_close and dh >= thr_far:
            collisions.append((int(a), int(b), d2d, dh))
    collisions.sort(key=lambda c: c[2])
    return collisions, duplicates


def sammon_stress(D_high: np.ndarray, D_low: np.ndarray) -> float:
    """Standard Sammon stress between high- and low-dimensional metrics."""
    iu = np.triu_indices(D_high.shape[0], k=1)
    d_hi, d_lo = D_high[iu], D_low[iu]
    mask = d_hi > 1e-12
    num = float(np.sum(((d_hi[mask] - d_lo[mask]) ** 2) / d_hi[mask]))
    den = float(np.sum(d_hi[mask]))
    return num / den if den > 0 else 0.0


def delta_rgb(rgb: np.ndarray, i: int, j: int) -> float:
    return float(np.linalg.norm(rgb[i] - rgb[j]))


ZONE_PATTERNS = {
    "soma": re.compile(r"^PART2_MIND_P(2[4-9]|3[01])_"),
    "duration": re.compile(r"^PART2_MIND_DEF_05(_C\d+)?$"),
    "potestas": re.compile(r"^PART2_MIND_P(3[7-9]|4\d|49)_"),
}
CHANNELS = ("r_red", "g_green", "b_blue")


def _point_biserial(indicator: np.ndarray, values: np.ndarray) -> float:
    if indicator.sum() in (0, len(indicator)):
        return 0.0
    if float(np.std(values)) < 1e-12:
        return 0.0
    return float(np.corrcoef(indicator, values)[0, 1])


def zone_channel_alignment(labels: list[str], rgb: np.ndarray) -> dict:
    """Falsifiable audit: does each Spinoza domain align to its channel?

    labels: chunk labels in reading order (aligned with rgb rows).
    rgb: (n, 3) matrix of channel intensities in [0,1].
    Verdicts: r_target >= 0.15 confirmed / <= -0.15 refuted / else neutral.
    """
    zones_report = []
    for zone_name, pattern in ZONE_PATTERNS.items():
        indicator = np.array([1.0 if pattern.match(lb) else 0.0
                              for lb in labels])
        entry = {"zone": zone_name,
                 "n": int(indicator.sum()),
                 "verdict": "neutral"}
        channel_key = {"soma": CHANNELS[0],
                       "duration": CHANNELS[1],
                       "potestas": CHANNELS[2]}[zone_name]
        for key, col in zip(CHANNELS, range(3)):
            entry[key] = round(_point_biserial(indicator, rgb[:, col]), 4)
        r_target = entry[channel_key]
        if r_target >= 0.15:
            entry["verdict"] = "confirmed"
        elif r_target <= -0.15:
            entry["verdict"] = "refuted"
        zones_report.append(entry)
    return {"hypothesis": {
                "soma": "r_red", "duration": "g_green", "potestas": "b_blue"},
            "zones": zones_report}


def load_nodes(db_path: Path):

    sql = """
        SELECT id, text, vector_blob FROM manifold_nodes m
        WHERE m.lifecycle_state != 'telemetry_error'
          AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
        ORDER BY CAST(SUBSTR(m.id, 6) AS INTEGER), m.id
    """

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    if len(rows) < 10:
        raise SystemExit(f"ERR: need >= 10 nodes in {db_path}, got {len(rows)}")
    node_ids = [r[0] for r in rows]
    texts = [" ".join(r[1].split()) for r in rows]
    X = np.vstack([np.frombuffer(r[2], dtype=np.float64) for r in rows])
    return node_ids, texts, X


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()


    node_ids, texts, X = load_nodes(args.db)
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))

    five_d = effective_5d(X)
    pts2d = five_d[:, 0:2]
    rgb = five_d[:, 2:5]

    collisions, duplicates = find_collisions(pts2d, X)

    collision_rows = [{
        "pair": f"{node_ids[c[0]]}<->{node_ids[c[1]]}",
        "labels": [labels.get(node_ids[c[0]]), labels.get(node_ids[c[1]])],
        "d2d": round(c[2], 4),
        "d384": round(c[3], 4),
        "delta_rgb": round(delta_rgb(rgb, c[0], c[1]), 4),
        "chromatically_rescuable":
            delta_rgb(rgb, c[0], c[1]) > RGB_DISCERNIBLE_THRESHOLD,
    } for c in collisions]
    rescued = sum(1 for row in collision_rows if row["chromatically_rescuable"])

    duplicate_rows = [{
        "pair": f"{node_ids[i]}<->{node_ids[j]}",
        "labels": [labels.get(node_ids[i]), labels.get(node_ids[j])],
        "note": "stylistic duplicate (identical text); not rescuable",
    } for i, j, _ in duplicates]

    D384 = pairwise_dists(X)
    stress_2d = sammon_stress(D384, pairwise_dists(pts2d))
    stress_5d = sammon_stress(D384, pairwise_dists(five_d[:, 0:5]))

    payload = {
        "n_points": len(node_ids),
        "channel_weighting": "singular_value_weighted_pc3_pc5_minmax",
        "explained_variance_top5": explained_top5(X),
        "sammon": {
            "stress_2d": round(stress_2d, 4),
            "stress_5d": round(stress_5d, 4),
            "decompression_gain_pct":
                round(100.0 * (stress_2d - stress_5d) / max(stress_2d, 1e-12), 2),
        },
        "collisions": {
            "thresholds": {"close_pct": 5.0, "far_pct": 95.0,
                           "rgb_discernible": RGB_DISCERNIBLE_THRESHOLD},
            "count": len(collision_rows),
            "rescued_chromatically": rescued,
            "rescue_rate": round(rescued / len(collision_rows), 4)
            if collision_rows else None,
            "rows": collision_rows[:50],
        },
        "stylistic_duplicates": duplicate_rows,
        "ontological_alignment": zone_channel_alignment(
            [labels[nid] for nid in node_ids], rgb),
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2)
                              + "\n", encoding="utf-8")

    print(f"[+] points: {len(node_ids)}")
    print(f"[=] Sammon stress: 2D={stress_2d:.4f} 5D={stress_5d:.4f} "
          f"(gain {payload['sammon']['decompression_gain_pct']:.1f}%)")
    print(f"[=] collisions: {len(collision_rows)} | chromatically rescued: "
          f"{rescued} ({payload['collisions']['rescue_rate']})")
    print(f"[=] stylistic duplicates: {len(duplicate_rows)}")
    for z in payload["ontological_alignment"]["zones"]:
        channel_key = payload["ontological_alignment"]["hypothesis"][z["zone"]]
        print(f"    {z['zone']:9} n={z['n']:>3} verdict={z['verdict']:9} "
              f"{channel_key}={z[channel_key]}")
    print(f"[+] output: {args.out}")
    return 0


def explained_top5(X) -> list[float]:

    Xc = X - np.mean(X, axis=0)
    S = np.linalg.svd(Xc, compute_uv=False)
    total = float(np.sum(S**2))
    return [round(float(v / total), 4) for v in S**2][:5]


if __name__ == "__main__":
    raise SystemExit(main())
