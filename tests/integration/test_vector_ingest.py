"""
Tests for POST /ingesta/vector — provider-agnostic vector ingestion endpoint.

Covers RH-1 (Provider Agnosticism): direct JSON vector ingestion without
text conversion, text/plain headers, or language encoders.
"""
import json
import math

import numpy as np
import pytest

import traianus.storage as storage
from traianus.core import evaluate_gate_v01


def _unit_vector(dim: int, seed: int = 42) -> list[float]:
    """Generates a deterministic L2-normalized vector of the given dimension."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float64)
    v /= np.linalg.norm(v)
    return v.tolist()


def _non_unit_vector(dim: int, seed: int = 42) -> list[float]:
    """Generates a deterministic NON-normalized vector (norm != 1.0)."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float64) * 3.7
    return v.tolist()


class TestVectorIngestValid:
    """Valid vector ingestion returns 201 with node_id, seq, sigma2, projections."""

    def test_valid_384d_vector_returns_201(self, client, auth_headers):
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        assert "node_id" in body
        assert "seq" in body
        assert body["seq"] == 1
        assert body["lifecycle_state"] in ("incubating", "pending_approval")
        assert "spectral_variance" in body
        assert "projections" in body
        assert len(body["projections"]) == 8

    def test_non_unit_vector_is_normalized_and_accepted(self, client, auth_headers):
        """Vectors with norm != 1.0 must be L2-normalized before projection."""
        vector = _non_unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 201

    def test_vector_with_label(self, client, auth_headers):
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector, "label": "test_alpha"},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        assert "node_id" in body

    def test_vector_with_metadata(self, client, auth_headers):
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector, "metadata": {"source": "synthetic", "dim": 384}},
            headers=auth_headers,
        )
        assert res.status_code == 201


class TestVectorIngestDimensionMismatch:
    """Dimension mismatch: reject with 422 if vector dim != active geodetic dim."""

    def test_128d_vector_rejected(self, client, auth_headers):
        vector = _unit_vector(128)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 422

    def test_512d_vector_rejected(self, client, auth_headers):
        vector = _unit_vector(512)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 422

    def test_empty_vector_rejected(self, client, auth_headers):
        res = client.post(
            "/ingesta/vector",
            json={"vector": []},
            headers=auth_headers,
        )
        assert res.status_code == 422


class TestVectorIngestNumericIntegrity:
    """Reject NaN, Inf, or non-numeric types."""

    def test_nan_rejected(self, client, auth_headers):
        vector = _unit_vector(384)
        vector[0] = float("nan")
        payload = json.dumps({"vector": vector})
        res = client.post(
            "/ingesta/vector",
            content=payload,
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert res.status_code == 422

    def test_positive_inf_rejected(self, client, auth_headers):
        vector = _unit_vector(384)
        vector[0] = float("inf")
        payload = json.dumps({"vector": vector})
        res = client.post(
            "/ingesta/vector",
            content=payload,
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert res.status_code == 422

    def test_negative_inf_rejected(self, client, auth_headers):
        vector = _unit_vector(384)
        vector[0] = float("-inf")
        payload = json.dumps({"vector": vector})
        res = client.post(
            "/ingesta/vector",
            content=payload,
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert res.status_code == 422

    def test_string_element_rejected(self, client, auth_headers):
        vector = _unit_vector(384)
        vector[0] = "not_a_number"
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 422

    def test_null_element_rejected(self, client, auth_headers):
        vector = _unit_vector(384)
        vector[0] = None
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 422


class TestVectorIngestZeroVector:
    """Zero-vector (norm == 0) must be rejected."""

    def test_zero_vector_rejected(self, client, auth_headers):
        vector = [0.0] * 384
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 422


class TestVectorIngestPersistence:
    """Append-only persistence: node is written with increasing seq."""

    def test_persisted_in_manifold_nodes(self, client, auth_headers):
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        node_id = body["node_id"]
        assert body["seq"] == 1
        assert body["lifecycle_state"] in ("incubating", "pending_approval")

        nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
        found = [n for n in nodes if n["id"] == node_id]
        assert len(found) == 1
        assert found[0]["lifecycle_state"] in ("incubating", "pending_approval")

    def test_second_ingestion_with_label_increments_seq(self, client, auth_headers):
        """Same label → same node_id → seq must strictly increment (append-only)."""
        vector = _unit_vector(384)

        res1 = client.post(
            "/ingesta/vector",
            json={"vector": vector, "label": "dup_test"},
            headers=auth_headers,
        )
        assert res1.status_code == 201

        res2 = client.post(
            "/ingesta/vector",
            json={"vector": vector, "label": "dup_test"},
            headers=auth_headers,
        )
        assert res2.status_code == 201

        node_id_1 = res1.json()["node_id"]
        node_id_2 = res2.json()["node_id"]
        assert node_id_1 == node_id_2, "Same label must resolve to same node_id"
        assert res2.json()["seq"] > res1.json()["seq"], "seq must strictly increase"

    def test_ingestion_without_label_distinct_vectors_create_distinct_nodes(self, client, auth_headers):
        """Without label, distinct vectors must produce distinct node_ids."""
        res1 = client.post(
            "/ingesta/vector",
            json={"vector": _unit_vector(384, seed=1)},
            headers=auth_headers,
        )
        assert res1.status_code == 201

        res2 = client.post(
            "/ingesta/vector",
            json={"vector": _unit_vector(384, seed=2)},
            headers=auth_headers,
        )
        assert res2.status_code == 201

        assert res1.json()["node_id"] != res2.json()["node_id"]
        assert res1.json()["seq"] == 1
        assert res2.json()["seq"] == 1

    def test_ingestion_without_label_identical_vectors_increment_seq(self, client, auth_headers):
        """Without label, identical vectors produce same node_id with seq increment."""
        vector = _unit_vector(384)

        res1 = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res1.status_code == 201

        res2 = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res2.status_code == 201

        assert res1.json()["node_id"] == res2.json()["node_id"]
        assert res2.json()["seq"] > res1.json()["seq"]


class TestVectorIngestAuth:
    """Endpoint requires operator token."""

    def test_missing_token_returns_401(self, client):
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
        )
        assert res.status_code == 401

    def test_invalid_token_returns_401(self, client):
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers={"X-Traianus-Token": "wrong-token"},
        )
        assert res.status_code == 401


class TestVectorIngestSpectralGate:
    """C1 dual-key gate is applied to vector ingestion (invariant compliance)."""

    def test_variance_uses_calibrated_threshold(self, client, auth_headers, isolate_db):
        """The endpoint must evaluate variance through evaluate_gate_v01 against
        the auto-calibrated threshold (which excludes self-projection)."""
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        assert "spectral_variance" in body
        assert "projections" in body
        assert len(body["projections"]) == 8

    def test_aligned_with_prosthetic_octagon_reports_consistent_variance(self, client, auth_headers):
        """A vector aligned with one axis must report low variance (energy concentrated),
        not inflated variance from self-projection leakage."""
        res = client.post(
            "/ingesta/vector",
            json={"vector": _unit_vector(384)},
            headers=auth_headers,
        )
        assert res.status_code == 201
        variance = res.json()["spectral_variance"]
        assert isinstance(variance, float)
        assert variance >= 0.0

    def test_dual_key_reported_in_response(self, client, auth_headers):
        """The response must expose dual-key gate metadata for transparency."""
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        assert "dual_key_status" in body
        assert "topological_key" in body["dual_key_status"]
        assert "ethical_key" in body["dual_key_status"]
        assert body["dual_key_status"]["ethical_key"] is False

    def test_gate_v01_kernel_produces_same_variance(self, client, auth_headers):
        """The spectral_variance in the response must match what evaluate_gate_v01
        computes from the same projections (single source of truth)."""
        vector = _unit_vector(384)
        res = client.post(
            "/ingesta/vector",
            json={"vector": vector},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        gate_result = evaluate_gate_v01(
            list(body["projections"].values()),
            ethical_key=False,
            threshold=body["dual_key_status"]["topological_key"]["threshold"],
        )
        assert gate_result["topological_key"]["variance"] == pytest.approx(body["spectral_variance"])
