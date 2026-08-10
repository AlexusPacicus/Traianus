#!/usr/bin/env python
"""Split a markdown manifest into paragraphs and test them through the real
Traianus kernel (offline encoder + real geodetic basis + dual-key gate).

Reads ONLY (no DB writes, no server): the geodetic basis is loaded from
`traianus.db` (read-only) and each paragraph is encoded locally with the
offline sentence-transformer model, L2-normalized, projected onto the real
axes, and evaluated against the calibrated dynamic threshold. Aggregates the
consolidation rate over this corpus.
"""

import argparse
import os
import re
import sqlite3
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np

sys.path.insert(0, os.path.abspath("."))

from traianus import app as main_module
from traianus.core import calibrate_critical_threshold, evaluate_gate_v01

DB_PATH = "traianus.db"


def load_geodesic_axes(db_path: str = DB_PATH) -> list[np.ndarray]:
    """Reads the active geodetic basis BLOBs (read-only, schema-agnostic)."""
    conn = sqlite3.connect(db_path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(geodesic_axes)").fetchall()]
        if "epoch_provenance" in cols:
            epoch = conn.execute(
                "SELECT epoch_provenance FROM geodesic_axes "
                "GROUP BY epoch_provenance ORDER BY MAX(created_at) DESC LIMIT 1"
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT vector_blob FROM geodesic_axes "
                "WHERE epoch_provenance = ? ORDER BY id",
                (epoch,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT vector_blob FROM geodesic_axes ORDER BY id").fetchall()
    finally:
        conn.close()
    return [np.frombuffer(row[0], dtype=np.float64) for row in rows]


def split_manifest(path: str, min_len: int = 20) -> list[str]:
    """Splits the manifest into paragraph units.

    The source is a wall of text (paragraphs are single lines, not blank-line
    separated). Each non-empty line is one unit; extraction fragments shorter
    than `min_len` chars (broken math subscripts, zero-width debris) are
    dropped.
    """
    text = open(path, encoding="utf-8").read()
    paragraphs = []
    for raw in text.split("\n"):
        para = re.sub(r"\s+", " ", raw).strip()
        if not para or re.fullmatch(r"[\s\u200b\u200c\u200d\ufeff]+", para):
            continue
        if len(para) < min_len:
            continue
        paragraphs.append(para)
    return paragraphs


def evaluate(paragraph: str, axis_vectors: list[np.ndarray], threshold: float) -> dict:
    """Encodes, normalizes, projects and gates one paragraph (server pipeline)."""
    native = main_module._encode_vector(paragraph)
    norm = np.linalg.norm(native)
    v = native / norm if norm > 0 else native
    projections = [float(np.dot(v, axis)) for axis in axis_vectors]
    variance = float(np.var(projections))
    gate = evaluate_gate_v01(projections, True, threshold)
    return {"variance": variance, "state": gate["state"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", nargs="?",
                        help="path to the markdown manifest to analyze (agnostic to location)")
    parser.add_argument("--min-len", type=int, default=20, help="drop fragments shorter than this (chars)")
    parser.add_argument("--index", type=int, action="append", metavar="N",
                        help="evaluate only paragraph N (1-based; repeatable). Default: all.")
    parser.add_argument("--list", action="store_true",
                        help="print paragraph index + preview without encoding (no model load).")
    args = parser.parse_args()

    if args.input_file is None:
        print("ERR: input_file argument missing.", file=sys.stderr)
        print("usage: python tools/experiments/ingest_manifest.py <path-to-markdown-manifest>", file=sys.stderr)
        return 2
    if not os.path.isfile(args.input_file):
        print(f"ERR: input file not found: {args.input_file}", file=sys.stderr)
        return 2

    paragraphs = split_manifest(args.input_file, args.min_len)
    print(f"[+] Input file: {args.input_file}")
    print(f"[+] Paragraphs: {len(paragraphs)}")

    if args.list:
        for i, para in enumerate(paragraphs, 1):
            print(f"  #{i:03d} ({len(para):4d}) | {para[:64].replace(chr(10), ' ')}")
        return 0

    axis_vectors = load_geodesic_axes()
    if not axis_vectors:
        print("ERR: geodesic_axes is empty (run traianus-bootstrap)")
        return 1
    threshold = calibrate_critical_threshold(axis_vectors)
    print(f"[+] theta_dyn (tissue density): {threshold:.6f}")

    selected = sorted(set(args.index or range(1, len(paragraphs) + 1)))
    consolidated = 0
    for i in selected:
        para = paragraphs[i - 1]
        res = evaluate(para, axis_vectors, threshold)
        if res["state"] == "consolidated":
            consolidated += 1
        flag = "C" if res["state"] == "consolidated" else "I"
        preview = para[:64].replace("\n", " ")
        print(f"  {flag} #{i:03d} var={res['variance']:.6f} | {preview}")

    total = len(selected)
    rate = consolidated / total if total else 0.0
    print("-" * 78)
    print(f"[=] Result: {consolidated}/{total} consolidated ({rate:.1%})")
    degenerate = consolidated == 0 or consolidated == total
    if degenerate:
        print("[!] DEGENERATE GATE: single outcome on this corpus (guard C1).")
    else:
        print("[+] NON-DEGENERATE GATE: both outcomes observed (guard C1 OK).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
