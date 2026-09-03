"""Storage layer: SQLite engines and persistence (ADR-025 §2.1).

Single source of truth for the active database path is ``DB_PATH`` defined
in THIS package. ``_storage.get_db_connection()`` resolves it lazily at call
time, so ``storage.DB_PATH = X`` (tests, tools, bootstrap) takes effect
globally with no dual-patch sync. Backward compatible: every public symbol
of the former ``traianus/storage.py`` module is re-exported here.
"""

from traianus.storage._storage import (
    AUDIT_LOG_DDL,
    CONTROL_PLANE_DDL,
    DATA_PLANE_DDL,
    EVENT_ERROR,
    EVENT_RECALIBRATION_SIGNAL,
    GEODESIC_AXES_DDL,
    INGESTION_QUEUE_DDL,
    MANIFOLD_EDGES_DDL,
    MANIFOLD_NODES_DDL,
    StorageError,
    active_epoch,
    compute_epsilon_edges,
    enqueue_ingest,
    get_active_epoch_axes,
    get_current_dimension_db,
    get_current_edges,
    get_current_nodes,
    get_db_connection,
    get_geodetic_matrix_db,
    get_telemetry_errors,
    init_db,
    init_relational_tables,
    insert_axis,
    insert_edge_revision,
    insert_error_log,
    insert_node_revision,
    mark_queue_processed,
    next_edge_seq,
    next_node_seq,
    node_exists,
    persist_epsilon_edges,
    rebuild_epsilon_edges,
)
from traianus.storage.sqlite_engine import SQLiteEngine

DB_PATH = "traianus.db"

__all__ = [
    "AUDIT_LOG_DDL",
    "CONTROL_PLANE_DDL",
    "DATA_PLANE_DDL",
    "DB_PATH",
    "EVENT_ERROR",
    "EVENT_RECALIBRATION_SIGNAL",
    "GEODESIC_AXES_DDL",
    "INGESTION_QUEUE_DDL",
    "MANIFOLD_EDGES_DDL",
    "MANIFOLD_NODES_DDL",
    "SQLiteEngine",
    "StorageError",
    "active_epoch",
    "compute_epsilon_edges",
    "enqueue_ingest",
    "get_active_epoch_axes",
    "get_current_dimension_db",
    "get_current_edges",
    "get_current_nodes",
    "get_db_connection",
    "get_geodetic_matrix_db",
    "get_telemetry_errors",
    "init_db",
    "init_relational_tables",
    "insert_axis",
    "insert_edge_revision",
    "insert_error_log",
    "insert_node_revision",
    "mark_queue_processed",
    "next_edge_seq",
    "next_node_seq",
    "node_exists",
    "persist_epsilon_edges",
    "rebuild_epsilon_edges",
]
