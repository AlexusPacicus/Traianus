"""Storage layer: SQLite engines and persistence (ADR-025 §2.1).

Single source of truth for the active database path is ``DB_PATH`` defined
in THIS package. ``_storage.get_db_connection()`` resolves it lazily at call
time, so ``storage.DB_PATH = X`` (tests, tools, bootstrap) takes effect
globally with no dual-patch sync. Backward compatible: every public symbol
of the former ``traianus/storage.py`` module is re-exported here.
"""

from traianus.storage._storage import (
    DATA_PLANE_DDL,
    CONTROL_PLANE_DDL,
    INGESTION_QUEUE_DDL,
    MANIFOLD_NODES_DDL,
    MANIFOLD_EDGES_DDL,
    GEODESIC_AXES_DDL,
    AUDIT_LOG_DDL,
    EVENT_ERROR,
    EVENT_RECALIBRATION_SIGNAL,
    init_db,
    init_relational_tables,
    get_db_connection,
    get_geodetic_matrix_db,
    get_current_dimension_db,
    get_active_epoch_axes,
    insert_axis,
    enqueue_ingest,
    mark_queue_processed,
    insert_node_revision,
    insert_error_log,
    insert_edge_revision,
    next_node_seq,
    next_edge_seq,
    node_exists,
    get_current_nodes,
    get_telemetry_errors,
    compute_epsilon_edges,
    rebuild_epsilon_edges,
    persist_epsilon_edges,
    get_current_edges,
    StorageError,
    active_epoch,
)
from traianus.storage.sqlite_engine import SQLiteEngine

DB_PATH = "traianus.db"

__all__ = [
    "DB_PATH",
    "DATA_PLANE_DDL",
    "CONTROL_PLANE_DDL",
    "INGESTION_QUEUE_DDL",
    "MANIFOLD_NODES_DDL",
    "MANIFOLD_EDGES_DDL",
    "GEODESIC_AXES_DDL",
    "AUDIT_LOG_DDL",
    "EVENT_ERROR",
    "EVENT_RECALIBRATION_SIGNAL",
    "init_db",
    "init_relational_tables",
    "get_db_connection",
    "get_geodetic_matrix_db",
    "get_current_dimension_db",
    "get_active_epoch_axes",
    "insert_axis",
    "enqueue_ingest",
    "mark_queue_processed",
    "insert_node_revision",
    "insert_error_log",
    "insert_edge_revision",
    "next_node_seq",
    "next_edge_seq",
    "node_exists",
    "get_current_nodes",
    "get_telemetry_errors",
    "compute_epsilon_edges",
    "rebuild_epsilon_edges",
    "persist_epsilon_edges",
    "get_current_edges",
    "StorageError",
    "active_epoch",
    "SQLiteEngine",
]
