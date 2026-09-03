"""Concurrency block tests for SQLiteEngine - real WAL concurrency."""
import pytest
import asyncio
import numpy as np
import tempfile
import os
import sys
import time
from traianus.storage.sqlite_engine import SQLiteEngine


class TestSQLiteEngineConcurrency:
    """Block tests: real concurrency with WAL."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.engine = SQLiteEngine(self.db_path)
        # Pre-populate data
        for i in range(100):
            vec = np.random.default_rng(i).normal(size=384).astype(np.float64)
            self.engine.insert_data_plane(f"node_{i}", vec)
            self.engine.upsert_control_plane(f"node_{i}", i % 10, 1)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_concurrent_reads_during_background_write(self):
        """100 concurrent reads while background writer updates control_plane."""
        latencies = []
        stop_writer = asyncio.Event()

        async def background_writer():
            version = 2
            while not stop_writer.is_set():
                for i in range(100):
                    self.engine.upsert_control_plane(f"node_{i}", i % 10, version)
                version += 1
                await asyncio.sleep(0.01)  # 10ms intervals

        async def reader(node_id: str):
            start = time.perf_counter()
            self.engine.get_data_plane(node_id)
            self.engine.get_control_plane(node_id)
            latencies.append(time.perf_counter() - start)

        writer_task = asyncio.create_task(background_writer())

        # Launch 100 concurrent readers
        read_tasks = [reader(f"node_{i}") for i in range(100)]
        await asyncio.gather(*read_tasks)

        stop_writer.set()
        await writer_task

        # p99 latency bound (Python + SQLite overhead). Under a tracer
        # (coverage/debugger) every call is ~10x slower, so the bound
        # relaxes; the invariant under test is non-blocking reads, which
        # the assertion below still guards order-of-magnitude-wise.
        bound = 0.050 if sys.gettrace() else 0.005
        latencies.sort()
        p99 = latencies[int(0.99 * len(latencies))]
        assert p99 < bound, f"p99 latency {p99*1000:.2f}ms exceeds bound"

    @pytest.mark.asyncio
    async def test_high_throughput_write_burst(self):
        """1000 writes in burst without SQLITE_BUSY."""
        async def write_batch(start: int, count: int):
            for i in range(start, start + count):
                vec = np.random.default_rng(i).normal(size=384).astype(np.float64)
                self.engine.insert_data_plane(f"burst_{i}", vec)

        tasks = [write_batch(i * 100, 100) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify all written
        for i in range(1000):
            retrieved, _ = self.engine.get_data_plane(f"burst_{i}")
            assert retrieved is not None

    def test_wal_checkpoint_does_not_block_reads(self):
        """Manual checkpoint during reads."""
        # Write some data
        for i in range(50):
            vec = np.random.default_rng(i).normal(size=384).astype(np.float64)
            self.engine.insert_data_plane(f"chk_{i}", vec)

        # Checkpoint
        with self.engine._connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

        # Reads should still work
        for i in range(50):
            retrieved, _ = self.engine.get_data_plane(f"chk_{i}")
            assert retrieved is not None

    def test_schema_migration_idempotent(self):
        """Calling _init_schema twice should not error."""
        self.engine._init_schema()
        self.engine._init_schema()  # Second call
        # Should work normally
        vec = np.random.default_rng(99).normal(size=384).astype(np.float64)
        self.engine.insert_data_plane("migrate_test", vec)
        retrieved, _ = self.engine.get_data_plane("migrate_test")
        assert np.array_equal(retrieved, vec)

    def test_corrupt_blob_handling(self):
        """Corrupt blob should raise clear error, not crash."""
        with self.engine._connect() as conn:
            conn.execute(
                "INSERT INTO data_plane (node_id, seq, vector_blob, dimension) VALUES (?, ?, ?, ?)",
                ("corrupt", 1, b"not a valid float64 blob", 384)
            )

        with pytest.raises(ValueError, match="Dimension mismatch"):
            self.engine.get_data_plane("corrupt")

    @pytest.mark.asyncio
    async def test_concurrent_data_plane_reads(self):
        """Many concurrent data_plane reads."""
        async def read_many():
            for i in range(100):
                self.engine.get_data_plane(f"node_{i}")

        tasks = [read_many() for _ in range(10)]
        await asyncio.gather(*tasks)

    def test_transaction_rollback_on_error(self):
        """Transaction rolls back on error."""
        # This test verifies the transaction context manager rolls back
        vec = np.random.default_rng(1).normal(size=384).astype(np.float64)
        
        try:
            with self.engine._transaction() as conn:
                conn.execute("""
                    INSERT INTO data_plane (node_id, seq, vector_blob, dimension)
                    VALUES (?, ?, ?, ?)
                """, ("tx_test", 1, vec.tobytes(), 384))
                # Force an error
                raise ValueError("Forced rollback")
        except ValueError:
            pass

        # Should not have committed
        assert self.engine.get_data_plane("tx_test") is None