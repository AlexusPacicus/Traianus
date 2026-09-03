"""Wiring tests: PolarProjector closed-circuit in POST /ingesta (ADR-025 §2.3)."""
import numpy as np

from traianus.storage.sqlite_engine import SQLiteEngine


class TestPolarIngestaWiring:
    """ADR-025 §2.3 sequence over the real HTTP pipeline (hermetic encoder)."""

    def test_ingesta_writes_data_plane_unconditionally(self, client, ingesta, auth_headers, isolate_db):
        """Step 1: every accepted ingestion persists its float64 vector in data_plane."""
        res = ingesta("Polar wiring probe")
        assert res.status_code == 200
        node_id = f"NODE_{res.json()['ingestion_id']}"

        engine = SQLiteEngine(db_path=isolate_db)
        result = engine.get_data_plane(node_id)
        assert result is not None
        vector, dimension = result
        assert dimension == 384
        assert vector.shape == (384,)
        assert vector.dtype == np.float64
        assert np.all(np.isfinite(vector))
        assert abs(float(np.linalg.norm(vector)) - 1.0) < 1e-6

    def test_ingesta_control_cache_updated_in_band(self, client, ingesta, auth_headers, isolate_db):
        """Step 4: in-band evaluation keeps the manifold_nodes cache write."""
        res = ingesta("Control cache probe")
        assert res.status_code == 200
        node_id = f"NODE_{res.json()['ingestion_id']}"

        nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
        found = [n for n in nodes if n["id"] == node_id]
        assert len(found) == 1
        assert found[0]["lifecycle_state"] in ("pending_approval", "incubating", "consolidated")

    def test_recalibration_rows_carry_valid_band(self, client, ingesta, auth_headers, isolate_db):
        """Out-of-band evaluations (if any) log RECAL_* rows with a valid band."""
        for i in range(5):
            res = ingesta(f"Band probe {i}")
            assert res.status_code == 200

        telemetry = client.get("/telemetry", headers=auth_headers).json()
        recal_rows = [r for r in telemetry if r["id"].startswith("RECAL_")]
        for row in recal_rows:
            assert "band" in row["trace"]
            assert ("ALERT_HIGH" in row["trace"]) != ("ALERT_LOW" in row["trace"])
        assert isinstance(telemetry, list)
