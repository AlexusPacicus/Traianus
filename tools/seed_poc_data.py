#!/usr/bin/env python3
"""Seed POC data: load 8 realistic NSM axes from fixture into traianus.db."""

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from traianus.app import serialize_vector

FIXTURE_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "nsm_axes_8.json"
DB_PATH = Path(__file__).parent.parent / "traianus.db"
EPOCH = "PROSTHETIC_NSM_V1"


def main():
    with open(FIXTURE_PATH, encoding="utf-8") as fh:
        axes = json.load(fh)

    print(f"Cargando {len(axes)} ejes desde {FIXTURE_PATH}...")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")

    try:
        for entry in axes:
            vec = np.asarray(entry["vector"], dtype=np.float64)
            blob = serialize_vector(vec)
            conn.execute(
                """INSERT OR REPLACE INTO geodesic_axes
                   (id, simbolo, tag, vector_blob, epoch_provenance)
                   VALUES (?, ?, ?, ?, ?)""",
                (entry["id"], entry["simbolo"], entry["tag"], blob, EPOCH),
            )
            print(f"  ✓ {entry['id']} ({entry['simbolo']}) - {entry['tag']}")

        conn.commit()
        print(f"\n✓ {len(axes)} ejes cargados en epoch '{EPOCH}'")

        # Verificación
        cursor = conn.execute(
            "SELECT id, simbolo, tag FROM geodesic_axes WHERE epoch_provenance = ? ORDER BY id",
            (EPOCH,),
        )
        for row in cursor.fetchall():
            print(f"  Verificado: {row[0]} ({row[1]}) - {row[2]}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
