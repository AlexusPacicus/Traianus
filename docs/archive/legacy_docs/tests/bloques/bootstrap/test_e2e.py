"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: bootstrap — E2E with real model (Phase 6).

Full journey: the bootstrap extracts the geodesic octagon with the cached
real model (M3 offline), anchors it in SQLite and the resulting geometry is
realistic (off-diagonal cosine > 0, not orthonormal) and reproducible.
Normative: docs/archive/legacy_docs/development/tests/SPEC-bootstrap.md
Coverage: BO08"""
import numpy as np
import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "bootstrap_e2e.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_bootstrap_BO08_full_journey(realistic_db):
    # M3: the bootstrap encoder is built offline (local_files_only).
    encoder = gb.build_encoder()
    assert encoder is not None

    octagon = gb.extract_pure_octagon()
    assert len(octagon) == 8

    vectors = np.stack([data["vector"] for data in octagon.values()])
    gram = vectors @ vectors.T
    off = gram[~np.eye(len(vectors), dtype=bool)]
    # Realistic NSM geometry: off-diagonal cosine ≈ 0.23 (not 0.0).
    assert off.mean() > 0.05, "BO-08: the real NSM geometry is not orthonormal (≈0.23)"
    assert off.mean() < 0.5, "BO-08: the real NSM geometry is not degenerate"
