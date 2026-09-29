"""Integration: /spatial reads the overview in one frame per epoch; /spatial/calibrate fits it.

GET /spatial derives {id, x, y, z, l, c, h} for every current node in the frozen frame of the
active epoch and writes nothing (refuter R2). Before any frame exists it answers 409 rather than
drawing each node in its own coordinates. POST /spatial/calibrate is the one explicit write: it
fits the frame on the current nodes and appends a revision (AGENTS 4.1).
"""
import math
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from traianus import storage
from traianus.geometry.spatial_observables import (
    derive_spatial_observables,
    dominant_axis,
)


@pytest.fixture
def seeded_nodes(client, ingesta):
    """Three ingestions so the manifold has several nodes and a full basis."""
    for text in ("Primera entidad de prueba", "Segunda entidad de seguimiento",
                 "Tercera entidad distinta"):
        res = ingesta(text)
        assert res.status_code == 200
    client.get("/nodos")


def _counts():
    with sqlite3.connect(storage.DB_PATH) as conn:
        return tuple(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("manifold_nodes", "manifold_edges", "spatial_calibration"))


class TestSpatialEndpoint:
    def test_spatial_refuses_before_a_frame_exists(self, client, seeded_nodes, auth_headers):
        res = client.get("/spatial", headers=auth_headers)
        assert res.status_code == 409
        assert "calibrate" in res.json()["detail"]

    def test_calibrate_appends_revisions(self, client, seeded_nodes, auth_headers):
        first = client.post("/spatial/calibrate", headers=auth_headers)
        second = client.post("/spatial/calibrate", headers=auth_headers)
        assert (first.status_code, second.status_code) == (201, 201)
        assert (first.json()["seq"], second.json()["seq"]) == (1, 2)
        assert len(first.json()["ranking"]) == 8
        assert first.json()["sample_size"] >= 3

    def test_channels_after_calibration(self, client, seeded_nodes, auth_headers):
        client.post("/spatial/calibrate", headers=auth_headers)
        nodes = client.get("/spatial", headers=auth_headers).json()["nodes"]
        assert len(nodes) >= 3
        for node in nodes:
            assert all(isinstance(node[k], float) and math.isfinite(node[k])
                       for k in ("x", "y", "z", "l", "c", "h"))
            assert -1.0 <= node["x"] <= 1.0 and -1.0 <= node["y"] <= 1.0
            assert node["z"] == 0.0 and node["l"] == nodes[0]["l"]
            assert 0.0 <= node["c"] <= 1.0 and 0.0 <= node["h"] <= 1.0

    def test_spatial_writes_nothing(self, client, seeded_nodes, auth_headers):
        """R2: observing the map never changes the state it shows."""
        client.post("/spatial/calibrate", headers=auth_headers)
        before = _counts()
        for _ in range(3):
            assert client.get("/spatial", headers=auth_headers).status_code == 200
        assert _counts() == before

    def test_spatial_is_reproducible(self, client, seeded_nodes, auth_headers):
        """R1: same state, epoch and frame give the same map."""
        client.post("/spatial/calibrate", headers=auth_headers)
        a = client.get("/spatial", headers=auth_headers).json()
        b = client.get("/spatial", headers=auth_headers).json()
        assert a == b

    def test_both_routes_require_the_operator_token(self, client, seeded_nodes):
        assert client.get("/spatial").status_code == 401
        assert client.post("/spatial/calibrate").status_code == 401

    def test_spatial_returns_same_ids_as_nodos(self, client, seeded_nodes, auth_headers):
        client.post("/spatial/calibrate", headers=auth_headers)
        nodos_ids = {n["id"] for n in client.get("/nodos", headers=auth_headers).json()["nodes"]}
        spatial_ids = {n["id"] for n in client.get("/spatial", headers=auth_headers).json()["nodes"]}
        assert spatial_ids == nodos_ids


def _led_by(k, seed):
    v = 0.05 * np.random.default_rng(seed).standard_normal(384)
    v[k] += 1.0
    return v / np.linalg.norm(v)


def _revise(node_id, vector, state="incubating"):
    storage.insert_node_revision(
        node_id, "", "", state, 0.0, 0, main.serialize_vector(vector), "{}", storage.active_epoch()
    )


@pytest.fixture
def axis_nodes():
    """Eight nodes, node n0 with two revisions (axis 0 then axis 5) and a telemetry_error node."""
    _revise("n0", _led_by(0, 100))
    for k in range(1, 8):
        _revise(f"n{k}", _led_by(k, 100 + k))
    _revise("n0", _led_by(5, 200))
    _revise("bad", _led_by(3, 300), state="telemetry_error")


def _expected_axes():
    basis = {k: v["vector"] for k, v in storage.get_geodetic_matrix_db().items()}
    return {i: dominant_axis(v, basis) for i, v in storage.get_current_node_vectors().items()}


class TestSpatialAxis:
    def test_overview_nodes_carry_the_dominant_axis_of_the_current_vector(
        self, client, auth_headers, axis_nodes
    ):
        client.post("/spatial/calibrate", headers=auth_headers)
        nodes = client.get("/spatial", headers=auth_headers).json()["nodes"]
        expected = _expected_axes()
        assert {n["id"]: n["axis"] for n in nodes} == expected
        assert "bad" not in expected
        assert expected["n0"] == "AXIS_6" and expected["n3"] == "AXIS_4"

    def test_overview_keeps_every_other_key_and_value(self, client, auth_headers, axis_nodes):
        client.post("/spatial/calibrate", headers=auth_headers)
        basis = {k: v["vector"] for k, v in storage.get_geodetic_matrix_db().items()}
        frame = main._active_epoch_frame()
        nodes = client.get("/spatial", headers=auth_headers).json()["nodes"]
        vectors = storage.get_current_node_vectors()
        assert [n["id"] for n in nodes] == sorted(vectors)
        for node in nodes:
            rest = {k: v for k, v in node.items() if k != "axis"}
            assert rest == {
                "id": node["id"],
                **derive_spatial_observables(vectors[node["id"]], basis, frame),
            }

    def test_perspective_nodes_carry_the_dominant_axis(self, client, auth_headers, axis_nodes):
        client.post("/spatial/calibrate", headers=auth_headers)
        res = client.get("/spatial", params={"anchor": "n2"}, headers=auth_headers)
        assert res.status_code == 200
        nodes = res.json()["nodes"]
        assert {n["id"]: n["axis"] for n in nodes} == _expected_axes()
        assert all(set(n) == {"id", "x", "y", "z", "l", "c", "h", "axis"} for n in nodes)
        overview = client.get("/spatial", headers=auth_headers).json()["nodes"]
        for a, b in zip(nodes, overview, strict=True):
            assert (a["z"], a["l"], a["c"], a["h"]) == (b["z"], b["l"], b["c"], b["h"])

    def test_the_axis_is_read_not_written(self, client, auth_headers, axis_nodes):
        client.post("/spatial/calibrate", headers=auth_headers)
        before = _counts()
        for params in ({}, {"anchor": "n2"}):
            assert client.get("/spatial", params=params, headers=auth_headers).status_code == 200
        assert _counts() == before

    def test_error_paths_do_not_move(self, client, auth_headers, axis_nodes):
        assert client.get("/spatial", headers=auth_headers).status_code == 409
        assert client.get("/spatial").status_code == 401
        client.post("/spatial/calibrate", headers=auth_headers)
        res = client.get("/spatial", params={"anchor": "missing"}, headers=auth_headers)
        assert res.status_code == 404
