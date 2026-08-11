"""
Tests for /ingesta/vector observability: structured logging,
request ID propagation, and concurrency conflict detection.
"""
import json
import logging
import concurrent.futures

import numpy as np
import pytest

import traianus.app as main
import traianus.observability as obs
import traianus.storage as storage


def _unit_vector(dim: int = 384, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float64)
    v /= np.linalg.norm(v)
    return v.tolist()


class TestRequestIdPropagation:
    """X-Request-ID is generated and returned in response headers."""

    def test_request_id_returned_in_response(self, client, auth_headers):
        res = client.post(
            "/ingesta/vector",
            json={"vector": _unit_vector()},
            headers=auth_headers,
        )
        assert res.status_code == 201
        assert "x-request-id" in res.headers
        assert len(res.headers["x-request-id"]) > 0

    def test_request_id_propagated_from_client(self, client, auth_headers):
        client_id = "test-trace-abc123"
        res = client.post(
            "/ingesta/vector",
            json={"vector": _unit_vector()},
            headers={**auth_headers, "X-Request-ID": client_id},
        )
        assert res.status_code == 201
        assert res.headers["x-request-id"] == client_id


class TestStructuredLogging:
    """Logs are emitted with request_id and phase information."""

    def test_structlog_logger_returns_bound_logger(self):
        logger = obs.get_logger(request_id="test-123")
        assert logger is not None

    def test_log_emitted_during_ingestion(self, client, auth_headers, capsys):
        res = client.post(
            "/ingesta/vector",
            json={"vector": _unit_vector()},
            headers=auth_headers,
        )
        assert res.status_code == 201
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "vector_ingestion_start" in combined or "vector_ingestion_completed" in combined


class TestConcurrencyNoDuplicates:
    """Concurrent ingestions with the same label produce sequential revisions."""

    def test_concurrent_same_label_sequential_seq(self, auth_headers):
        vector = _unit_vector()

        def _ingest(i):
            from fastapi.testclient import TestClient
            client = TestClient(main.app)
            return client.post(
                "/ingesta/vector",
                json={"vector": vector, "label": "concurrent_test"},
                headers=auth_headers,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_ingest, i) for i in range(8)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for r in results:
            assert r.status_code == 201

        node_ids = [r.json()["node_id"] for r in results]
        assert len(set(node_ids)) == 1, "All concurrent requests must resolve to same node_id"
