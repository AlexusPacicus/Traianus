"""Integration: GET /spatial?anchor=<id> answers the perspective at a node.

The map is redrawn in the frame of one node: poles, fallback flag and the z-scored coordinates
(x, y) come from traianus.geometry.perspective on the persisted vectors and basis; z, l, c and h
stay the epoch channels of the overview, so a node keeps its colour across views. Read only
(refuters R1 and R2, AGENTS 4.3); without the parameter the route is the overview, unchanged.
"""
import sqlite3
from contextlib import closing

import numpy as np
import pytest

import traianus.app as main
from traianus import storage
from traianus.geometry.perspective import observe, perspective_frame, select_poles
from traianus.geometry.spatial_observables import derive_spatial_observables

STATES = ("incubating", "pending_approval", "consolidated")
INSERTION_ORDER = (3, 0, 5, 1, 4, 7, 2, 6)
NODE_KEYS = {"id", "x", "y", "z", "l", "c", "h"}


def _vector(k):
    """Unit vector led by axis k then k + 1, so each anchor has poles of its own."""
    v = 0.05 * np.random.default_rng(k).standard_normal(384)
    v[k % 8] += 1.0
    v[(k + 1) % 8] += 0.6
    return v / np.linalg.norm(v)


def _insert(node_id, vector, state="incubating"):
    storage.insert_node_revision(
        node_id, "", "", state, 0.0, 0, main.serialize_vector(vector), "{}", storage.active_epoch()
    )


@pytest.fixture
def uncalibrated():
    """Eight nodes inserted out of id order, one lifecycle state each in turn; no epoch frame."""
    for k in INSERTION_ORDER:
        _insert(f"n{k}", _vector(k), STATES[k % 3])


@pytest.fixture
def calibrated(client, auth_headers, uncalibrated):
    assert client.post("/spatial/calibrate", headers=auth_headers).status_code == 201


def _get(client, headers, anchor):
    return client.get("/spatial", params={"anchor": anchor}, headers=headers)


def _counts():
    with closing(sqlite3.connect(storage.DB_PATH)) as conn:
        return tuple(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("manifold_nodes", "manifold_edges", "spatial_calibration"))


def _state(node_id):
    with closing(sqlite3.connect(storage.DB_PATH)) as conn:
        return conn.execute(
            "SELECT lifecycle_state FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1",
            (node_id,),
        ).fetchone()[0]


def _expected(anchor):
    """(ids, poles, fallback, coordinates) of the anchor from the persisted vectors and basis."""
    vectors = storage.get_current_node_vectors()
    ids = sorted(vectors)
    matrix = np.vstack([vectors[i] for i in ids])
    basis = {k: v["vector"] for k, v in storage.get_geodetic_matrix_db().items()}
    index = ids.index(anchor)
    poles = select_poles(matrix[index], basis)
    perspective = perspective_frame(matrix[index], basis)
    dipole = perspective.frame
    coords = observe(matrix, index, horizontal=dipole.v_dipole / dipole.v_dipole_norm_sq)
    return ids, poles, perspective.fallback, coords


def test_t1_body_is_the_perspective_functions_output(client, auth_headers, calibrated):
    """T1: poles, fallback and the z-scored, unclipped (x, y) for two anchors, rows in id order."""
    poles_seen = []
    for anchor in ("n0", "n5"):
        ids, poles, fallback, coords = _expected(anchor)
        res = _get(client, auth_headers, anchor)
        assert res.status_code == 200
        body = res.json()
        assert body["anchor"] == anchor
        assert body["poles"] == list(poles)
        assert isinstance(body["fallback"], bool) and body["fallback"] == fallback
        assert [n["id"] for n in body["nodes"]] == ids
        assert all(set(n) == NODE_KEYS for n in body["nodes"])
        assert [n["x"] for n in body["nodes"]] == coords[:, 0].tolist()
        assert [n["y"] for n in body["nodes"]] == coords[:, 1].tolist()
        assert np.abs(coords).max() > 1.0
        poles_seen.append(poles)
    assert poles_seen[0] != poles_seen[1]


def test_t2_colour_is_the_epoch_channels_in_every_perspective(client, auth_headers, calibrated):
    """T2: z, l, c and h of every node equal the overview's, whatever the anchor."""
    overview = {n["id"]: n for n in client.get("/spatial", headers=auth_headers).json()["nodes"]}
    assert len({n["c"] for n in overview.values()}) > 1
    assert len({n["h"] for n in overview.values()}) > 1
    for anchor in ("n0", "n5", "n7"):
        res = _get(client, auth_headers, anchor)
        assert res.status_code == 200
        body = res.json()
        assert body["anchor"] == anchor
        assert {n["id"] for n in body["nodes"]} == set(overview)
        for node in body["nodes"]:
            for key in ("z", "l", "c", "h"):
                assert node[key] == overview[node["id"]][key]


@pytest.mark.parametrize("anchor", ["unknown", ""])
def test_t3_unknown_or_empty_anchor_is_404(client, auth_headers, calibrated, anchor):
    """T3: an id that is not a current node, and the empty id."""
    assert _get(client, auth_headers, anchor).status_code == 404


@pytest.mark.parametrize("anchor", ["n0", "unknown"])
def test_t3_no_frame_is_409_with_the_overview_detail_before_the_anchor_is_checked(
    client, auth_headers, uncalibrated, anchor
):
    """T3: the frame check comes first, so even an unknown anchor answers 409."""
    detail = client.get("/spatial", headers=auth_headers).json()["detail"]
    res = _get(client, auth_headers, anchor)
    assert (res.status_code, res.json()["detail"]) == (409, detail)


@pytest.mark.parametrize("headers", [{}, {"X-Traianus-Token": "wrong"}])
def test_t3_missing_or_wrong_token_is_401(client, calibrated, headers):
    """T3: the token dependency answers before anything about the anchor."""
    assert _get(client, headers, "n0").status_code == 401


def test_t4_perspective_writes_nothing_and_repeats_byte_for_byte(client, auth_headers, calibrated):
    """T4: R2 (no write) and R1 (same state, same body) for a perspective request."""
    before = _counts()
    first = _get(client, auth_headers, "n0")
    second = _get(client, auth_headers, "n0")
    assert first.status_code == second.status_code == 200
    assert first.json()["anchor"] == "n0"
    assert first.content == second.content
    assert _counts() == before


def test_t5_overview_without_anchor_is_unchanged(client, auth_headers, calibrated):
    """T5 (guard): only the nodes key, each node as derive_spatial_observables gives it."""
    body = client.get("/spatial", headers=auth_headers).json()
    basis = {k: v["vector"] for k, v in storage.get_geodetic_matrix_db().items()}
    vectors = storage.get_current_node_vectors()
    frame = main._active_epoch_frame()
    assert body == {"nodes": [
        {"id": i, **derive_spatial_observables(vectors[i], basis, frame)} for i in sorted(vectors)
    ]}


def test_t5_overview_with_an_empty_basis_is_still_an_empty_list(client, auth_headers, monkeypatch):
    """T5 (guard): without an anchor an empty basis is 200 with no nodes, not 409."""
    monkeypatch.setattr(main, "get_geodetic_matrix_db", dict)
    res = client.get("/spatial", headers=auth_headers)
    assert (res.status_code, res.json()) == (200, {"nodes": []})


def test_t6_a_value_error_from_the_perspective_is_422_with_its_message(client, auth_headers):
    """T6: the anchor is the only current node, so observe refuses N < 2."""
    _insert("only", _vector(0))
    assert client.post("/spatial/calibrate", headers=auth_headers).status_code == 201
    with pytest.raises(ValueError) as raised:
        observe(storage.get_current_node_vectors()["only"][None, :], 0)
    res = _get(client, auth_headers, "only")
    assert (res.status_code, res.json()["detail"]) == (422, str(raised.value))


@pytest.mark.parametrize("anchor,state", [
    ("n0", "incubating"), ("n1", "pending_approval"), ("n2", "consolidated"),
])
def test_t7_anchor_is_accepted_whatever_its_lifecycle_state(
    client, auth_headers, calibrated, anchor, state
):
    """T7: each state the fixtures reach; telemetry_error is not a current node (X2)."""
    assert _state(anchor) == state
    res = _get(client, auth_headers, anchor)
    assert res.status_code == 200
    assert res.json()["anchor"] == anchor
    assert res.json()["poles"] == list(_expected(anchor)[1])


def test_x1_empty_basis_with_an_anchor_is_409(client, auth_headers, uncalibrated, monkeypatch):
    """X1: with an anchor an empty basis answers 409 with the missing-frame detail."""
    detail = client.get("/spatial", headers=auth_headers).json()["detail"]
    assert client.post("/spatial/calibrate", headers=auth_headers).status_code == 201
    monkeypatch.setattr(main, "get_geodetic_matrix_db", dict)
    res = _get(client, auth_headers, "n0")
    assert (res.status_code, res.json()["detail"]) == (409, detail)


def test_x2_a_telemetry_error_id_is_not_a_current_node(client, auth_headers, calibrated):
    """X2: the reader excludes telemetry_error rows, so such an id answers 404."""
    storage.insert_error_log("err", "", "", 0.0, 0, main.serialize_vector(_vector(0)), "{}")
    assert _get(client, auth_headers, "err").status_code == 404
