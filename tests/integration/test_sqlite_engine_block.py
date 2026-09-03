"""Block tests for SQLiteEngine - realistic read/write cycles."""
import os
import tempfile

import numpy as np

from traianus.storage.sqlite_engine import SQLiteEngine


class TestSQLiteEngineBlock:
    """Block tests: realistic read/write cycles."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.engine = SQLiteEngine(self.db_path)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_read_write_cycle_data_plane(self):
        """Full cycle: write → read → verify for multiple dimensions."""
        for d in [384, 768, 1536]:
            vec = np.random.default_rng(d).normal(size=d).astype(np.float64)
            self.engine.insert_data_plane(f"cycle_{d}", vec)
            retrieved, dim = self.engine.get_data_plane(f"cycle_{d}")
            assert dim == d
            assert np.array_equal(retrieved, vec)

    def test_read_write_cycle_control_plane(self):
        """Full cycle with version increments."""
        for version in range(1, 6):
            self.engine.upsert_control_plane("versioned", 42, version)
            cid, ver = self.engine.get_control_plane("versioned")
            assert cid == 42
            assert ver == version

    def test_atomic_cross_plane_transaction(self):
        """Atomic write to both planes in single transaction."""
        vec = np.random.default_rng(999).normal(size=384).astype(np.float64)

        with self.engine._transaction() as conn:
            conn.execute("""
                INSERT INTO data_plane (node_id, seq, vector_blob, dimension)
                VALUES (?, ?, ?, ?)
            """, ("atomic_node", 1, vec.tobytes(), 384))

            conn.execute("""
                INSERT INTO control_plane (node_id, centroid_id, version)
                VALUES (?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    centroid_id = excluded.centroid_id,
                    version = excluded.version
            """, ("atomic_node", 7, 1))

        # Verify both committed
        retrieved_vec, dim = self.engine.get_data_plane("atomic_node")
        assert dim == 384
        assert np.array_equal(retrieved_vec, vec)

        cid, ver = self.engine.get_control_plane("atomic_node")
        assert cid == 7
        assert ver == 1

    def test_large_vector_storage_1536d(self):
        """Stress test: 1536D vectors (12KB each)."""
        vec = np.random.default_rng(1536).normal(size=1536).astype(np.float64)
        self.engine.insert_data_plane("large_1536", vec)
        retrieved, dim = self.engine.get_data_plane("large_1536")
        assert dim == 1536
        assert np.array_equal(retrieved, vec)

    def test_concurrent_versions_different_nodes(self):
        """Multiple nodes with independent version counters."""
        for node_id in ["node_a", "node_b", "node_c"]:
            for v in range(1, 4):
                self.engine.upsert_control_plane(node_id, hash(node_id) % 100, v)

        for node_id in ["node_a", "node_b", "node_c"]:
            cid, ver = self.engine.get_control_plane(node_id)
            assert ver == 3
            assert cid == hash(node_id) % 100

    def test_many_nodes_storage_retrieval(self):
        """Store and retrieve many nodes efficiently."""
        n_nodes = 500
        for i in range(n_nodes):
            vec = np.random.default_rng(i).normal(size=384).astype(np.float64)
            self.engine.insert_data_plane(f"many_{i}", vec)
            self.engine.upsert_control_plane(f"many_{i}", i % 20, 1)

        # Verify random sample
        for i in [0, 100, 250, 499]:
            retrieved, dim = self.engine.get_data_plane(f"many_{i}")
            assert dim == 384
            assert np.array_equal(retrieved, np.random.default_rng(i).normal(size=384).astype(np.float64))

            cid, ver = self.engine.get_control_plane(f"many_{i}")
            assert cid == i % 20
            assert ver == 1

    def test_update_existing_vector_same_dimension(self):
        """Update vector with same dimension."""
        vec1 = np.random.default_rng(1).normal(size=384).astype(np.float64)
        vec2 = np.random.default_rng(2).normal(size=384).astype(np.float64)

        self.engine.insert_data_plane("update_test", vec1)
        self.engine.insert_data_plane("update_test", vec2)

        retrieved, _ = self.engine.get_data_plane("update_test")
        assert np.array_equal(retrieved, vec2)

    def test_update_existing_vector_different_dimension(self):
        """Update vector with different dimension."""
        vec1 = np.random.default_rng(1).normal(size=384).astype(np.float64)
        vec2 = np.random.default_rng(2).normal(size=768).astype(np.float64)

        self.engine.insert_data_plane("dim_change", vec1)
        self.engine.insert_data_plane("dim_change", vec2)

        retrieved, dim = self.engine.get_data_plane("dim_change")
        assert dim == 768
        assert np.array_equal(retrieved, vec2)

    def test_control_plane_update_preserves_other_fields(self):
        """Updating control_plane preserves centroid_id if only version changes."""
        self.engine.upsert_control_plane("preserve", 99, 1)
        self.engine.upsert_control_plane("preserve", 99, 2)  # Same centroid, new version

        cid, ver = self.engine.get_control_plane("preserve")
        assert cid == 99
        assert ver == 2