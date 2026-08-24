"""C1 deduplication guard for the spectral-math-engine MCP server.

`calibrate_c1_threshold` re-implemented the canonical kernel from
`traianus.geometry.observables` — exactly the divergent-copy failure mode
warned about in tests/helpers/db_factory.py. The MCP layer must DELEGATE
the invariant-critical variance computation to the kernel and keep only
presentation concerns (normalization, reporting envelope).
"""
import numpy as np
import pytest

from tools.mcp import spectral_math_mcp as mcp_math
from traianus.geometry.observables import calibrate_critical_threshold as canonical_c1


def _ortho_rows(k: int = 8, d: int = 16) -> list[list[float]]:
    """Deterministic orthonormal rows (already on S^{d-1})."""
    rng = np.random.default_rng(7)
    q, _ = np.linalg.qr(rng.standard_normal((d, d)))
    return [q[i].tolist() for i in range(k)]


def test_c1_threshold_delegates_to_canonical_kernel(monkeypatch):
    monkeypatch.setattr(
        mcp_math, "_kernel_calibrate_critical_threshold", lambda vectors: 0.31415
    )
    out = mcp_math.calibrate_c1_threshold(_ortho_rows())
    assert out["critical_threshold"] == 0.31415


def test_c1_matches_canonical_kernel_on_normalized_basis():
    rows = _ortho_rows()
    out = mcp_math.calibrate_c1_threshold(rows)["critical_threshold"]
    expected = canonical_c1([np.array(r, dtype=np.float64) for r in rows])
    assert out == pytest.approx(expected)


def test_single_axis_returns_zero_threshold_not_crash():
    out = mcp_math.calibrate_c1_threshold([[1.0, 0.0, 0.0]])
    assert out["status"] == "SUCCESS"
    assert out["critical_threshold"] == 0.0
