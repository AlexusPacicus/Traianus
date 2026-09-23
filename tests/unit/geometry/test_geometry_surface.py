"""Regression: traianus.geometry no longer exposes the superseded SemanticSimplex
(traianus/geometry/simplex.py) or its RECALIBRATION_SIGNAL constant -- both lost to
VarianceTracker (traianus/telemetry/variance_tracker.py, ADR-025) and never had a
caller outside their own module.
"""
from traianus import geometry


def test_geometry_does_not_expose_semantic_simplex() -> None:
    assert not hasattr(geometry, "SemanticSimplex")
    assert not hasattr(geometry, "RECALIBRATION_SIGNAL")
    assert "SemanticSimplex" not in geometry.__all__
    assert "RECALIBRATION_SIGNAL" not in geometry.__all__
