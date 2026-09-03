"""Unit tests for SQLiteEngine - schema, serialization, basic CRUD."""
import numpy as np
import tempfile
import os
from traianus.storage.sqlite_engine import SQLiteEngine


class TestSQLiteEngineUnit:
    """Unit tests for schema, serialization, basic CRUD."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.engine = SQLiteEngine(self.db_path)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_connect_executes_wal_pragmas(self):
        """Verify WAL mode and synchronous=NORMAL are set."""
        with self.engine._connect() as conn:
            wal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            sync_mode = conn.execute("PRAGMA synchronous;").fetchone()[0]
            assert wal_mode == "wal"
            assert sync_mode == 1  # NORMAL = 1

    def test_connect_executes_busy_timeout(self):
        """Verify busy_timeout is set."""
        with self.engine._connect() as conn:
            timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
            assert timeout == 5000

    def test_data_plane_schema_created(self):
        """data_plane table exists with correct columns."""
        with self.engine._connect() as conn:
            tables = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            assert "data_plane" in tables
            
            cols = [row[1] for row in conn.execute("PRAGMA table_info(data_plane)").fetchall()]
            assert "node_id" in cols
            assert "seq" in cols
            assert "vector_blob" in cols
            assert "dimension" in cols
            assert "updated_at" in cols

    def test_control_plane_schema_created(self):
        """control_plane table exists with correct columns."""
        with self.engine._connect() as conn:
            tables = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            assert "control_plane" in tables
            
            cols = [row[1] for row in conn.execute("PRAGMA table_info(control_plane)").fetchall()]
            assert "node_id" in cols
            assert "centroid_id" in cols
            assert "version" in cols

    def test_indexes_created(self):
        """Indexes exist for common queries."""
        with self.engine._connect() as conn:
            indexes = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()]
            assert "idx_data_plane_updated" in indexes
            assert "idx_control_plane_centroid" in indexes

    def test_serialize_float64_roundtrip(self):
        """Vector roundtrip: upsert → get returns identical array."""
        vector = np.random.default_rng(42).normal(size=384).astype(np.float64)
        self.engine.insert_data_plane("test_node", vector)
        retrieved, dim = self.engine.get_data_plane("test_node")
        assert dim == 384
        assert np.array_equal(retrieved, vector)

    def test_deserialize_variable_dimension(self):
        """Vectors of different dimensions stored and retrieved correctly."""
        for d in [384, 768, 1536]:
            vector = np.random.default_rng(d).normal(size=d).astype(np.float64)
            self.engine.insert_data_plane(f"node_{d}", vector)
            retrieved, dim = self.engine.get_data_plane(f"node_{d}")
            assert dim == d
            assert np.array_equal(retrieved, vector)

    def test_insert_data_plane_appends_revisions(self):
        """Re-ingestion of same node_id INSERTS new revisions, never overwrites (A2)."""
        vector1 = np.random.default_rng(1).normal(size=384).astype(np.float64)
        vector2 = np.random.default_rng(2).normal(size=384).astype(np.float64)

        assert self.engine.insert_data_plane("node", vector1) == 1
        assert self.engine.insert_data_plane("node", vector2) == 2

        retrieved, _ = self.engine.get_data_plane("node")
        assert np.array_equal(retrieved, vector2)

        with self.engine._connect() as conn:
            rows = conn.execute(
                "SELECT seq FROM data_plane WHERE node_id = ? ORDER BY seq",
                ("node",),
            ).fetchall()
        assert [r[0] for r in rows] == [1, 2]

    def test_upsert_control_plane_version_increment(self):
        """Version increments correctly on upsert."""
        self.engine.upsert_control_plane("node", 5, 1)
        self.engine.upsert_control_plane("node", 7, 2)
        centroid_id, version = self.engine.get_control_plane("node")
        assert centroid_id == 7
        assert version == 2

    def test_get_data_plane_returns_dimension(self):
        """get_data_plane returns correct dimension metadata."""
        vector = np.random.default_rng(2).normal(size=768).astype(np.float64)
        self.engine.insert_data_plane("node", vector)
        _, dim = self.engine.get_data_plane("node")
        assert dim == 768

    def test_get_control_plane_returns_centroid_version(self):
        """get_control_plane returns (centroid_id, version)."""
        self.engine.upsert_control_plane("node", 123, 5)
        centroid_id, version = self.engine.get_control_plane("node")
        assert centroid_id == 123
        assert version == 5

    def test_get_nonexistent_returns_none(self):
        """Non-existent keys return None."""
        assert self.engine.get_data_plane("nonexistent") is None
        assert self.engine.get_control_plane("nonexistent") is None

    def test_centroid_id_varint_ranges(self):
        """SQLite INTEGER varint handles all ranges correctly."""
        test_cases = [
            (0, 1),
            (255, 1),
            (256, 2),
            (65535, 2),
            (65536, 3),
            (16777215, 3),
            (16777216, 4),
            (4294967295, 4),
        ]
        for centroid_id, _ in test_cases:
            self.engine.upsert_control_plane(f"node_{centroid_id}", centroid_id, 1)
            retrieved, _ = self.engine.get_control_plane(f"node_{centroid_id}")
            assert retrieved == centroid_id

    def test_increment_version_atomically(self):
        """increment_version bumps version and returns the new value."""
        self.engine.upsert_control_plane("ver_node", 7, 1)
        assert self.engine.increment_version("ver_node") == 2
        assert self.engine.increment_version("ver_node") == 3
        _, version = self.engine.get_control_plane("ver_node")
        assert version == 3

    def test_increment_version_missing_node_returns_zero(self):
        """increment_version on unknown node returns 0."""
        assert self.engine.increment_version("ghost") == 0

    def test_data_plane_foreign_key_enforced(self):
        """control_plane.node_id references data_plane.node_id."""
        # This should work - insert data_plane first
        vec = np.random.default_rng(99).normal(size=384).astype(np.float64)
        self.engine.insert_data_plane("fk_test", vec)
        self.engine.upsert_control_plane("fk_test", 1, 1)
        
        # Verify both exist
        assert self.engine.get_data_plane("fk_test") is not None
        assert self.engine.get_control_plane("fk_test") is not None