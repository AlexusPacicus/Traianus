import sqlite3
import os
import secrets
from contextlib import asynccontextmanager
import numpy as np
import json
from typing import List, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# =====================================================================
# OFFLINE GUARD (audit M3): offline sovereignty. Model must be prefetched
# locally; no HF Hub downloads at runtime. First run is the only one that
# requires network (prefetch via bootstrap/setup).
# =====================================================================
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def build_encoder():
    return SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)


def _startup_create_schema():
    """Creates the relational schema on the active DB_PATH at server boot.

    Import is side-effect free by design: `traianus.app` does NOT open a
    database or load the encoder at import time (hermeticity, L1). Both
    artifacts are created lazily — the schema on server startup, the encoder
    on first `get_model()` call.
    """
    init_db()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _startup_create_schema()
    yield


app = FastAPI(
    title="Project Traianus - Deterministic Customs v5",
    lifespan=lifespan,
)

# =====================================================================
# ENUMERATED CORS (audit H3): no wildcard. Only the local observation
# client (Ulpia/RefApp in dev) can call with credentials.
# =====================================================================

ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Lazy encoder (hermetic import, L1): the model is NOT built at import time.
# Import of `traianus.app` is side-effect free; `get_model()` loads the encoder
# on first use and caches it. Unit tests run without the model (fake injected).
_model = None


def get_model():
    global _model
    if _model is None:
        _model = build_encoder()
    return _model


DB_PATH = "traianus.db"

# =====================================================================
# SERVER-SIDE EPSILON FOR DETERMINISTIC E_n (ADR-023/H5, RE-09/CO-12)
# Epsilon is a server-side constant, never a client parameter (Zero-Trust).
# Configurable only at boot via TRAIANUS_EPSILON_EDGE.
# =====================================================================
EPSILON_EDGE = float(os.environ.get("TRAIANUS_EPSILON_EDGE", "0.8"))

# =====================================================================
# ZERO-TRUST INGRESS PERIMETER (audit H2): ALLOWLIST.
# Everything that is not text/plain is rejected at the perimeter with 415.
# =====================================================================

ALLOWED_INGRESS_TYPES = {"text/plain"}


# =====================================================================
# LOCAL OPERATOR TOKEN (audit H3): routes that mutate state (or expose
# sensitive observability) require a local operator token. Fail-closed:
# if TRAIANUS_TOKEN is not defined in the environment, every protected
# route responds 401. The key is read per-request to allow injection in
# tests and rotation without restart.
# =====================================================================

def require_token(x_traianus_token: str = Header(default="")):
    token = os.environ.get("TRAIANUS_TOKEN", "")
    if not token or not secrets.compare_digest(x_traianus_token, token):
        raise HTTPException(status_code=401, detail="Missing/invalid operator token.")

# =====================================================================
# OFFICIAL PYDANTIC DATA CONTRACTS (CONTRACTS_AND_PRISMS.md)
# =====================================================================

LifecycleState = Literal[
    "pending_approval",
    "consolidated",
    "incubating",
    "telemetry_error",
    "archived",
]

class RawDump(BaseModel):
    text: str = Field(..., description="Raw external entity payload content in plain text.")
    type: str = Field(default="text/plain", description="MIME payload type. Non-plain text payloads are rejected at perimeter.")

class RefinedEntity(BaseModel):
    text: str = Field(..., description="Structured entity payload content in plain text.")
    lifecycle_state: LifecycleState = Field(..., description="State attribute.")
    revision_milestone: bool = Field(default=False, description="Ethical Key marker.")
    projections: List[float] = Field(..., description="Full multi-axis projection spectrum array.")

class ConsolidationBody(BaseModel):
    text: str = Field(..., description="Structured entity payload content in plain text.")
    ethical_key: bool = Field(..., description="Explicit Ethical Key (HITL) human operator confirmation. Required; omitted or false keeps the node out of consolidation (ADR-022).")

class HitlRelation(BaseModel):
    source: str
    target: str
    state: str

def init_relational_tables():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # =================================================================
        # H4 — APPEND-ONLY NODE LOG (invariant #1 ADR-025 / §6.2)
        # Intent_Class: the node log is immutable; every state transition
        #   INSERTS a new revision with increasing `seq` per `id`.
        # Runtime_Contract: composite PK (id, seq); never UPDATE/REPLACE/
        #   DELETE on manifold_nodes; "current state" = MAX(seq) per id.
        # Implementation_Block: revision log DDL below.
        # Topological_Grounding: ADR-025 §"Monotonic Append-Only Evolution"
        # (docs/architecture/ADR/ADR.md:126, literal quote, one line):
        # "State evolution $S_n \to S_{n+1}$ is append-only. Historical vertices, deterministic edges, and simplicial faces in persistent storage are immutable."
        # Safety_Abort: if the legacy schema cannot be migrated without loss,
        #   the transaction aborts (rollback) and the error propagates.
        # =================================================================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manifold_nodes (
                id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                text TEXT NOT NULL,
                toon_factor TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                action_potential REAL NOT NULL,
                revision_milestone INTEGER NOT NULL,
                vector_blob BLOB NOT NULL,
                projections_json TEXT NOT NULL,
                sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, seq)
            )
        """)
        # Schema migration for pre-H4 DBs (derived artifact): each existing
        # node becomes its revision seq=1. History is preserved.
        legacy_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(manifold_nodes)").fetchall()
        ]
        if legacy_cols and "seq" not in legacy_cols:
            conn.execute("ALTER TABLE manifold_nodes RENAME TO manifold_nodes_legacy")
            conn.execute("""
                CREATE TABLE manifold_nodes (
                    id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    toon_factor TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    action_potential REAL NOT NULL,
                    revision_milestone INTEGER NOT NULL,
                    vector_blob BLOB NOT NULL,
                    projections_json TEXT NOT NULL,
                    sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, seq)
                )
            """)
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential,
                 revision_milestone, vector_blob, projections_json)
                SELECT id, 1, text, toon_factor, lifecycle_state, action_potential,
                       revision_milestone, vector_blob, projections_json
                FROM manifold_nodes_legacy
            """)
            conn.execute("DROP TABLE manifold_nodes_legacy")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manifold_edges (
                id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                state TEXT NOT NULL,
                sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, seq)
            )
        """)
        # Schema migration for pre-H4 DBs: each existing edge becomes its
        # revision seq=1. History is preserved (append-only invariant #1).
        legacy_edge_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(manifold_edges)").fetchall()
        ]
        if legacy_edge_cols and "seq" not in legacy_edge_cols:
            conn.execute("ALTER TABLE manifold_edges RENAME TO manifold_edges_legacy")
            conn.execute("""
                CREATE TABLE manifold_edges (
                    id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    state TEXT NOT NULL,
                    sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, seq)
                )
            """)
            conn.execute("""
                INSERT INTO manifold_edges (id, seq, source, target, state)
                SELECT id, 1, source, target, state FROM manifold_edges_legacy
            """)
            conn.execute("DROP TABLE manifold_edges_legacy")

def init_db():
    """Initializes relational tables at the active DB_PATH.

    The audit harness (tools/audit_harness.py) and hermetic tests
    reassign `DB_PATH` after import; this alias allows recreating the
    schema (ingestion_queue, manifold_nodes, manifold_edges) on the active
    database before anchoring the geodetic baseline or ingesting nodes.
    """
    init_relational_tables()

# =====================================================================
# VECTOR UTILITIES
# =====================================================================

def serialize_vector(vector: np.ndarray) -> bytes:
    return vector.astype(np.float64).tobytes()

def next_node_seq(conn: sqlite3.Connection, node_id: str) -> int:
    """
    Next revision sequence for a node in the append-only log (H4).
    For a new id returns 1; for an existing one, MAX(seq) + 1.
    """
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM manifold_nodes WHERE id = ?",
        (node_id,),
    ).fetchone()
    return int(row[0])

def next_edge_seq(conn: sqlite3.Connection, edge_id: str) -> int:
    """
    Next revision sequence for an edge in the append-only log (H4).
    For a new id returns 1; for an existing one, MAX(seq) + 1.
    """
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM manifold_edges WHERE id = ?",
        (edge_id,),
    ).fetchone()
    return int(row[0])

def get_geodetic_matrix_db() -> dict:
    """
    Loads the geodetic baseline from SQLite.

    Returns {axis_id: {"symbol": str, "vector": np.ndarray}} keyed by the
    unique axis id (e.g. `AXIS_1`). Reconstructing keys from `simbolo`/`tag`
    via string concatenation is ambiguous (tags carry a leading underscore,
    e.g. `_SOMETHING_HAPPENS`), which collapsed the projection spectrum to a
    single key when parsed with `key.split("_")[1]`.
    """
    matrix = {}
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, simbolo, tag, vector_blob FROM geodesic_axes ORDER BY id")
            rows = cursor.fetchall()
            for axis_id, symbol, tag, blob in rows:
                vec = np.frombuffer(blob, dtype=np.float64)
                matrix[axis_id] = {"symbol": symbol, "vector": vec}
        except sqlite3.OperationalError:
            pass
    return matrix

def get_current_dimension_db() -> int:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("SELECT vector_blob FROM geodesic_axes LIMIT 1")
            row = cursor.fetchone()
        if row:
            axis_vector = np.frombuffer(row[0], dtype=np.float64)
            return len(axis_vector)
        return 384
    except Exception:
        return 384

def auto_calibrate_critical_threshold() -> float:
    matrix = get_geodetic_matrix_db()
    if not matrix:
        raise RuntimeError("[Traianus Core] Error: Geodetic matrix empty. Aborting autocalibration.")
    vectors = [entry["vector"] for entry in matrix.values()]
    base_variances = []
    for i, axis_vector in enumerate(vectors):
        # Cross projections only (j != i). Self-projection (dot == 1.0
        # for an L2-normalized axis) inflated the baseline to an
        # unreachable scale for inputs, forcing the Topological Key to a
        # 0% approval rate on real corpora. Finding C1.
        projections = [
            float(np.dot(axis_vector, other))
            for j, other in enumerate(vectors) if j != i
        ]
        base_variances.append(np.var(projections))
    return float(np.mean(base_variances))

# =====================================================================
# ASYNCHRONOUS GEOMETRIC ROUTING
# =====================================================================

def async_spectral_processor(ingestion_id: int, raw_text: str):
    try:
        native_vector = get_model().encode(raw_text)
        geodetic_matrix = get_geodetic_matrix_db()
        if not geodetic_matrix:
            raise RuntimeError(
                "[Traianus Core] Critical infrastructure failure: geodetic_axes table is empty. "
                "Run `traianus-bootstrap` (traianus.bootstrap:main) to bootstrap the geodetic baseline before ingestion."
            )

        dim_db = get_current_dimension_db()
        dim_in = len(native_vector)

        if dim_in > dim_db:
            raise ValueError(
                f"[Traianus Core] Dimension mismatch rejected: provider vector dim={dim_in} "
                f"exceeds geodetic baseline dim={dim_db} (I-6.2/L6)."
            )
        if dim_db > dim_in:
            padded_vector = np.pad(native_vector, (0, dim_db - dim_in), mode='constant', constant_values=0.0)
        else:
            padded_vector = native_vector

        norm = np.linalg.norm(padded_vector)
        norm_idea_vector = padded_vector / norm if norm > 0 else padded_vector

        projections = {}
        for axis_id, axis_entry in geodetic_matrix.items():
            projections[axis_id] = float(np.dot(norm_idea_vector, axis_entry["vector"]))

        variance = float(np.var(list(projections.values())))

        dominant_attractor = max(
            geodetic_matrix.keys(),
            key=lambda k: np.dot(norm_idea_vector, geodetic_matrix[k]["vector"]),
        )
        toon_symbol = geodetic_matrix[dominant_attractor]["symbol"]

        lifecycle_state: LifecycleState = "pending_approval"
        # action_potential derives from the projection spectrum without magic
        # constants (ADR-005); the old *10.0 had no declared semantics (M6).
        action_potential = float(variance)

        validated_entity = RefinedEntity(
            text=raw_text,
            lifecycle_state=lifecycle_state,
            revision_milestone=False,
            projections=list(projections.values()),
        )
        # L5 (audit): persist what we validate. projections_json is derived
        # from the VALIDATED projections (RefinedEntity.projections), not from
        # the raw dict, so the contract is the single source of truth.
        projections_json = json.dumps({
            axis_id: float(value)
            for axis_id, value in zip(geodetic_matrix.keys(), validated_entity.projections)
        })

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            node_id = f"NODE_{ingestion_id}"
            seq = next_node_seq(conn, node_id)
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id, seq, raw_text, toon_symbol,
                validated_entity.lifecycle_state, action_potential,
                int(validated_entity.revision_milestone),
                serialize_vector(norm_idea_vector), projections_json
            ))
            conn.execute("UPDATE ingestion_queue SET status = 'PROCESSED' WHERE id = ?", (ingestion_id,))

        print(f"[Traianus Core] Idea #{ingestion_id} registered in limbo. Variance: {variance:.4f}")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                log_id = f"LOG_{ingestion_id}"
                seq = next_node_seq(conn, log_id)
                conn.execute("""
                    INSERT INTO manifold_nodes
                    (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_id, seq,
                    f"[ValidationError / StructuralDrift] ingestion_id={ingestion_id}\n\n{error_trace}",
                    "▱",
                    "telemetry_error",
                    0.0,
                    0,
                    b"",
                    json.dumps({"error": str(e)})
                ))
        except Exception:
            pass

# =====================================================================
# FRONTEND CUSTOMS OPERATIONAL ENDPOINTS
# =====================================================================

@app.post("/ingesta", dependencies=[Depends(require_token)])
async def frontend_ingestion_endpoint(dump: RawDump, background_tasks: BackgroundTasks):
    if dump.type not in ALLOWED_INGRESS_TYPES:
        raise HTTPException(status_code=415, detail="Only text/plain is accepted at ingress.")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cur = conn.execute("INSERT INTO ingestion_queue (payload) VALUES (?)", (dump.text,))
            ingestion_id = cur.lastrowid
    except sqlite3.Error as e:
        raise HTTPException(status_code=503, detail="Ingress persistence unavailable.") from e
    background_tasks.add_task(async_spectral_processor, ingestion_id, dump.text)
    return {"status": "accepted", "ingestion_id": ingestion_id}

@app.post("/nodos/{node_id}/consolidar", dependencies=[Depends(require_token)])
async def consolidate_sovereignty(node_id: str, body: ConsolidationBody):
    try:
        native_vector = get_model().encode(body.text)
        geodetic_matrix = get_geodetic_matrix_db()

        dim_db = get_current_dimension_db()
        dim_in = len(native_vector)
        if dim_in > dim_db:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Provider dimension {dim_in} exceeds geodetic baseline {dim_db}; "
                    "dimension mismatch rejected (I-6.2/L6)."
                ),
            )
        if dim_db > dim_in:
            padded_vector = np.pad(native_vector, (0, dim_db - dim_in), mode='constant', constant_values=0.0)
        else:
            padded_vector = native_vector

        norm = np.linalg.norm(padded_vector)
        norm_idea_vector = padded_vector / norm if norm > 0 else padded_vector

        projections = {}
        for axis_id, axis_entry in geodetic_matrix.items():
            projections[axis_id] = float(np.dot(norm_idea_vector, axis_entry["vector"]))

        variance = float(np.var(list(projections.values())))
        dynamic_threshold = auto_calibrate_critical_threshold()

        dominant_attractor = max(
            geodetic_matrix.keys(),
            key=lambda k: np.dot(norm_idea_vector, geodetic_matrix[k]["vector"]),
        )
        toon_symbol = geodetic_matrix[dominant_attractor]["symbol"]

        topological_key_passed = variance >= dynamic_threshold
        ethical_key_passed = body.ethical_key

        # Dual-Key Consolidation (ADR-022):
        # State consolidation requires concurrent satisfaction of the
        # Topological Key AND the Ethical Key.
        if topological_key_passed and ethical_key_passed:
            new_state: LifecycleState = "consolidated"
            action_pot = 1.0
        else:
            new_state: LifecycleState = "incubating"
            action_pot = float(variance)

        revision_milestone_val = 1 if ethical_key_passed else 0

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            # H4: consolidation INSERTS a new revision with increasing seq;
            # never overwrites the original row (UPDATE was prohibited).
            exists = cursor.execute(
                "SELECT 1 FROM manifold_nodes WHERE id = ?", (node_id,)
            ).fetchone()
            if exists is None:
                raise HTTPException(status_code=404, detail=f"Node {node_id} not found.")
            seq = next_node_seq(conn, node_id)
            cursor.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential,
                 revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, seq, body.text, toon_symbol, new_state, action_pot,
                  revision_milestone_val,
                  serialize_vector(norm_idea_vector), json.dumps(projections)))

            # H5/ADR-023 + RE-09/CO-12: persist deterministic E_n
            # (auto-edge-*) over current MAX(seq) vectors, in the SAME
            # transaction as the revision. Unconditional (both consolidated
            # and incubating branches). Any sqlite3.Error propagates to the
            # outer except -> HTTP 500 + rollback (H1/M5: no fake SUCCESS).
            persist_epsilon_edges(EPSILON_EDGE, conn=conn)

        return {
            "status": "SUCCESS",
            "new_state": new_state,
            "dual_key_status": {
                "topological_key": topological_key_passed,
                "ethical_key": ethical_key_passed,
                "consolidated": topological_key_passed and ethical_key_passed,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/nodos")
async def get_manifold_nodes():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, toon_factor, lifecycle_state, action_potential,
                       revision_milestone, projections_json
                FROM manifold_nodes m
                WHERE lifecycle_state != 'telemetry_error'
                  AND seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
                ORDER BY id DESC
            """)
            rows = cursor.fetchall()

        serialized_nodes = []
        for row in rows:
            serialized_nodes.append({
                "id": row[0], "text": row[1], "toon_factor": row[2],
                "lifecycle_state": row[3], "action_potential": float(row[4]),
                "revision_milestone": int(row[5]),
                "projections_json": json.loads(row[6])
            })
        return {"status": "SUCCESS", "nodes": serialized_nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/telemetry", dependencies=[Depends(require_token)])
async def get_telemetry_logs():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, projections_json, sys_internal_timestamp
                FROM manifold_nodes m
                WHERE lifecycle_state = 'telemetry_error'
                  AND seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
                ORDER BY sys_internal_timestamp DESC
            """)
            rows = cursor.fetchall()
        return [
            {"id": r[0], "trace": r[1], "meta": json.loads(r[2]), "time": r[3]}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/relations", dependencies=[Depends(require_token)])
async def get_relations():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, source, target, state
                FROM manifold_edges e
                WHERE state != 'removed'
                  AND seq = (SELECT MAX(seq) FROM manifold_edges e2 WHERE e2.id = e.id)
                ORDER BY id
            """)
            rows = cursor.fetchall()
        return [
            {"id": r[0], "source": r[1], "target": r[2], "state": r[3]}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/relations", dependencies=[Depends(require_token)])
async def forge_relation(relation: HitlRelation):
    try:
        nodes = sorted([relation.source, relation.target])
        edge_id = f"edge-{nodes[0]}-{nodes[1]}"

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            # L2 (audit): dangling edges not allowed. Each endpoint
            # must exist as a node in manifold_nodes; if not, 4xx (404).
            for endpoint in (relation.source, relation.target):
                exists = cursor.execute(
                    "SELECT 1 FROM manifold_nodes WHERE id = ? LIMIT 1",
                    (endpoint,),
                ).fetchone()
                if exists is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Node {endpoint} not found. Dangling edge rejected (L2).",
                    )
            # H4: edges are an append-only revision log. Re-forging an edge
            # INSERTS a new revision with increasing seq; the previous one is
            # never overwritten (no UPDATE / ON CONFLICT DO UPDATE).
            seq = next_edge_seq(conn, edge_id)
            cursor.execute("""
                INSERT INTO manifold_edges (id, seq, source, target, state)
                VALUES (?, ?, ?, ?, ?)
            """, (edge_id, seq, relation.source, relation.target, relation.state))

        return {"status": "SUCCESS", "id": edge_id, "state": relation.state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# INTERACTIVE LOGOGRAPHIC GENESIS (ADR-015)
# =====================================================================

def _current_node_vectors(conn: sqlite3.Connection) -> dict[str, np.ndarray]:
    """Current-state vectors (MAX(seq) per id), excluding telemetry_error.

    Shared DB read for E_n reconstruction/persistence (ADR-023/H5, RE-08/RE-09):
    telemetry_error log rows are not part of the manifold (mirrors /nodos).
    """
    rows = conn.execute("""
        SELECT m.id, m.vector_blob
        FROM manifold_nodes m
        WHERE m.lifecycle_state != 'telemetry_error'
          AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
    """).fetchall()
    return {nid: np.frombuffer(blob, dtype=np.float64) for nid, blob in rows}


def _compute_epsilon_edges(nodes: dict[str, np.ndarray], epsilon: float) -> list[dict]:
    """Pure ε-adjacency computation (ADR-023/H5, RE-08): no DB access.

    (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ epsilon. Deterministic: nodes are
    processed in sorted id order and edges are sorted by (source, target).
    """
    ids = sorted(nodes)
    edges: list[dict] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            dist = float(np.linalg.norm(nodes[ids[i]] - nodes[ids[j]]))
            if dist <= epsilon:
                edges.append({
                    "source": ids[i],
                    "target": ids[j],
                    "distance": round(dist, 6),
                })
    edges.sort(key=lambda e: (e["source"], e["target"]))
    return edges


def rebuild_epsilon_edges(epsilon: float) -> list[dict]:
    """Deterministic E_n (ADR-023/H5, RE-08): (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ epsilon.

    Reads current states (MAX(seq)) from manifold_nodes (telemetry_error
    excluded), projects L2 vectors, and returns ε-adjacent edges. Does not
    mutate DB: E_n reconstruction is a pure function over persisted state.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        nodes = _current_node_vectors(conn)
    return _compute_epsilon_edges(nodes, epsilon)


def persist_epsilon_edges(epsilon: float, conn: sqlite3.Connection | None = None) -> int:
    """Persists deterministic E_n as auto-edge-<src>-<tgt> rows (RE-09, ADR-023/H5).

    Append-only (H4): never UPDATE/DELETE. State transitions are recorded as
    new revisions with increasing seq:
      * a newly adjacent pair (or one previously 'removed') INSERTS state='auto';
      * a pair that is no longer ε-adjacent INSERTS a tombstone state='removed'.
    The current view (get_relations) exposes MAX(seq) per id and excludes
    'removed'. Manual edge-* rows are preserved. Excludes telemetry_error nodes.
    If `conn` is provided, operates inside that transaction (no commit — the
    caller owns the transaction); otherwise opens its own connection and
    commits. Returns the number of currently adjacent auto edges.
    """
    owns_conn = conn is None
    if owns_conn:
        conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        nodes = _current_node_vectors(conn)
        edges = _compute_epsilon_edges(nodes, epsilon)
        desired = {f"auto-edge-{e['source']}-{e['target']}" for e in edges}

        prev = {
            r[0]: (r[1], r[2], r[3])
            for r in conn.execute("""
                SELECT id, source, target, state
                FROM manifold_edges e
                WHERE id LIKE 'auto-edge-%'
                  AND seq = (SELECT MAX(seq) FROM manifold_edges e2 WHERE e2.id = e.id)
            """).fetchall()
        }

        for edge in edges:
            edge_id = f"auto-edge-{edge['source']}-{edge['target']}"
            if prev.get(edge_id) is None or prev[edge_id][2] != "auto":
                seq = next_edge_seq(conn, edge_id)
                conn.execute(
                    "INSERT INTO manifold_edges (id, seq, source, target, state) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (edge_id, seq, edge["source"], edge["target"], "auto"),
                )

        for edge_id in prev:
            if edge_id not in desired:
                seq = next_edge_seq(conn, edge_id)
                source, target, _ = prev[edge_id]
                conn.execute(
                    "INSERT INTO manifold_edges (id, seq, source, target, state) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (edge_id, seq, source, target, "removed"),
                )

        if owns_conn:
            conn.commit()
        return len(edges)
    finally:
        if owns_conn:
            conn.close()

@app.post("/mutate/{new_symbol}", dependencies=[Depends(require_token)])
async def logographic_genesis(new_symbol: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()

            cursor.execute("SELECT id, vector_blob FROM geodesic_axes")
            current_axes = cursor.fetchall()
            if not current_axes:
                raise HTTPException(status_code=400, detail="Geodetic baseline not initialized.")

            sample_vector = np.frombuffer(current_axes[0][1], dtype=np.float64)
            current_dimension = len(sample_vector)
            new_dimension = current_dimension + 1

            for axis_id, blob in current_axes:
                axis_vector = np.frombuffer(blob, dtype=np.float64)
                axis_vector_pad = np.pad(axis_vector, (0, 1), mode='constant', constant_values=0.0)
                cursor.execute(
                    "UPDATE geodesic_axes SET vector_blob = ? WHERE id = ?",
                    (serialize_vector(axis_vector_pad), axis_id)
                )

            new_axis = np.zeros(new_dimension)
            new_axis[-1] = 1.0
            new_id = f"T{len(current_axes) + 1}"

            cursor.execute("""
                INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob)
                VALUES (?, ?, ?, ?)
            """, (new_id, new_symbol, "_CUSTOM", serialize_vector(new_axis)))

            cursor.execute("""
                SELECT id, seq, text, toon_factor, lifecycle_state, action_potential,
                       revision_milestone, vector_blob, projections_json
                FROM manifold_nodes m
                WHERE seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
            """)
            nodes = cursor.fetchall()
            for node_id, cur_seq, ntext, toon, life, apot, rms, blob, pjson in nodes:
                node_vector = np.frombuffer(blob, dtype=np.float64)
                if len(node_vector) < new_dimension:
                    node_vector_pad = np.pad(
                        node_vector, (0, new_dimension - len(node_vector)),
                        mode='constant', constant_values=0.0
                    )
                    # H4: dimensional expansion INSERTS a new revision
                    # with padded vector; the previous revision remains intact.
                    cursor.execute(
                        "INSERT INTO manifold_nodes (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (node_id, next_node_seq(conn, node_id), ntext, toon, life, apot, rms,
                         serialize_vector(node_vector_pad), pjson)
                    )

        return {
            "status": "SUCCESS",
    "message": f"Logographic Genesis completed. Hyperspace expanded to {new_dimension}D.",
    "new_axis": f"{new_symbol}_CUSTOM"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
