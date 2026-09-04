"""Integration: GET /spatial read-only observables endpoint (Ulpia Fase 0).

The /spatial endpoint derives per-node spatial observables
(x, y, z, l, c, h) from persisted current states (observational, no writes).
Mirrors /relations (ADR-023/H5): computed on read, no lifecycle mutation.
"""
import math

import pytest


@pytest.fixture
def seeded_nodes(client, ingesta):
    """Two ingestions so the manifold has multiple nodes and a full basis."""
    for text in ("Primera entidad de prueba", "Segunda entidad de seguimiento"):
        res = ingesta(text)
        assert res.status_code == 200
    # Let the background spectral processor run to completion.
    client.get("/nodos")


class TestSpatialEndpoint:
    def test_spatial_endpoint_returns_channel_map(self, client, seeded_nodes, auth_headers):
        res = client.get("/spatial", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
        assert len(data["nodes"]) >= 2

    def test_spatial_channels_are_normalized_and_finite(self, client, seeded_nodes, auth_headers):
        data = client.get("/spatial", headers=auth_headers).json()
        for node in data["nodes"]:
            assert "id" in node
            for key in ("x", "y", "z", "l", "c", "h"):
                assert key in node
                val = node[key]
                assert isinstance(val, float)
                assert 0.0 <= val <= 1.0
                assert math.isfinite(val)

    def test_spatial_is_observational_no_state_mutation(self, client, seeded_nodes, auth_headers):
        """GET /spatial must not alter lifecycle state or create nodes."""
        before = sorted(n["id"] for n in client.get("/nodos", headers=auth_headers).json()["nodes"])
        res = client.get("/spatial", headers=auth_headers)
        assert res.status_code == 200
        after = sorted(n["id"] for n in client.get("/nodos", headers=auth_headers).json()["nodes"])
        assert before == after

    def test_spatial_requires_operator_token(self, client, seeded_nodes):
        res = client.get("/spatial")
        assert res.status_code == 401

    def test_spatial_returns_same_ids_as_nodos(self, client, seeded_nodes, auth_headers):
        nodos_ids = {n["id"] for n in client.get("/nodos", headers=auth_headers).json()["nodes"]}
        spatial_ids = {n["id"] for n in client.get("/spatial", headers=auth_headers).json()["nodes"]}
        assert spatial_ids == nodos_ids
