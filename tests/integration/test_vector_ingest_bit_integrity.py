"""Integration: /ingesta/vector stores the vectors K6 measures (contracts.md §0, engine path).

The engine is loaded with the frozen artefact's vectors one at a time (POC.md, Corpus loading).
K6 measures v_hat = row / sqrt(row @ row) in binary64 over the artefact's binary32 rows widened
exactly (tools/experiments/k6_colour_predictability.py, contracts.md §0 Conversions), so the
stored BLOB must be those bytes: little-endian binary64, 384 x 8. Re-normalising is not the
identity on these rows, so the received bits and the measured bits differ, and only the measured
ones are the contract. Rows are built as the artefact is (raw and its norm in binary32, division
in binary32). A flipped bit must show in the stored bytes (contracts.md §0, bit flips).
"""
import sqlite3
import uuid

import numpy as np
import pytest

from traianus import storage

DIM = 384


def _artefact_row(seed):
    raw = np.random.default_rng(seed).standard_normal(DIM).astype(np.float32)
    return raw / np.linalg.norm(raw)


def _measured(row):
    row64 = row.astype("<f8")
    return row64 / np.sqrt(row64 @ row64)


def _flip(row, index, bit):
    bits = row.view(np.uint32).copy()
    bits[index] ^= np.uint32(1 << bit)
    return bits.view(np.float32)


def _stored(node_id):
    with sqlite3.connect(storage.DB_PATH) as conn:
        (blob,) = conn.execute(
            "SELECT vector_blob FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1",
            (node_id,),
        ).fetchone()
    return blob


def _load(client, auth_headers, label, row):
    res = client.post(
        "/ingesta/vector",
        json={"vector": row.astype(np.float64).tolist(), "label": label},
        headers={**auth_headers, "X-Idempotency-Key": uuid.uuid4().hex},
    )
    assert res.status_code == 201
    return _stored(res.json()["node_id"])


def test_stored_bits_are_the_vectors_k6_measures(client, auth_headers):
    rows = [_artefact_row(seed) for seed in range(20)]
    assert any(_measured(row).tobytes() != row.astype("<f8").tobytes() for row in rows)
    mismatched = []
    for seed, row in enumerate(rows):
        blob = _load(client, auth_headers, f"row{seed}", row)
        assert len(blob) == DIM * 8
        if blob != _measured(row).tobytes():
            mismatched.append(seed)
    assert mismatched == []


@pytest.mark.parametrize("index, bit", [(0, 31), (5, 0), (100, 22), (7, 23)])
def test_one_flipped_bit_shows_in_the_stored_bytes(client, auth_headers, index, bit):
    row = _artefact_row(3)
    flipped = _flip(row, index, bit)
    assert flipped.tobytes() != row.tobytes()
    original = _load(client, auth_headers, "original", row)
    changed = _load(client, auth_headers, "flipped", flipped)
    assert changed != original
    assert changed == _measured(flipped).tobytes()
