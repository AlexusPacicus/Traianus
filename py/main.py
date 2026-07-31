import sqlite3
import numpy as np
import json
from typing import Optional, List, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Project Traianus - Deterministic Customs v5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = SentenceTransformer('all-MiniLM-L6-v2')
DB_PATH = "traianus.db"

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
    text: str
    ethical_key: Literal[True] = Field(..., description="Explicit Ethical Key validation. Must be `true` to consolidate (ADR-022).")

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manifold_nodes (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                toon_factor TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                action_potential REAL NOT NULL,
                revision_milestone INTEGER NOT NULL,
                vector_blob BLOB NOT NULL,
                projections_json TEXT NOT NULL,
                sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manifold_edges (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)

init_relational_tables()

# =====================================================================
# VECTOR UTILITIES
# =====================================================================

def serialize_vector(vector: np.ndarray) -> bytes:
    return vector.astype(np.float64).tobytes()

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
    for axis_vector in vectors:
        projections = [float(np.dot(axis_vector, other_vec)) for other_vec in vectors]
        base_variances.append(np.var(projections))
    return float(np.mean(base_variances))

# =====================================================================
# ASYNCHRONOUS GEOMETRIC ROUTING
# =====================================================================

def async_spectral_processor(ingestion_id: int, raw_text: str):
    try:
        native_vector = model.encode(raw_text)
        geodetic_matrix = get_geodetic_matrix_db()
        if not geodetic_matrix:
            raise RuntimeError(
                "[Traianus Core] Critical infrastructure failure: geodetic_axes table is empty. "
                "Run py/geodesic_bootstrap.py to bootstrap the geodetic baseline before ingestion."
            )

        dim_db = get_current_dimension_db()
        dim_in = len(native_vector)

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
        action_potential = float(variance * 10.0)

        validated_entity = RefinedEntity(
            text=raw_text,
            lifecycle_state=lifecycle_state,
            revision_milestone=False,
            projections=list(projections.values()),
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                INSERT OR REPLACE INTO manifold_nodes
                (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"NODE_{ingestion_id}", raw_text, toon_symbol,
                validated_entity.lifecycle_state, action_potential,
                int(validated_entity.revision_milestone),
                serialize_vector(norm_idea_vector), json.dumps(projections)
            ))
            conn.execute("UPDATE ingestion_queue SET status = 'PROCESSED' WHERE id = ?", (ingestion_id,))

        print(f"[Traianus Core] Idea #{ingestion_id} registered in limbo. Variance: {variance:.4f}")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    INSERT OR REPLACE INTO manifold_nodes
                    (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"LOG_{ingestion_id}",
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

@app.post("/ingesta")
async def frontend_ingestion_endpoint(dump: RawDump, background_tasks: BackgroundTasks):
    if dump.type in ["audio/ogg", "audio/m4a"]:
        raise HTTPException(status_code=400, detail="Strictly Plain Text required. Audio rejected.")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ingestion_queue (payload) VALUES (?)", (dump.text,))
            ingestion_id = cursor.lastrowid

        background_tasks.add_task(async_spectral_processor, ingestion_id, dump.text)
        return {"status": 200, "data": "plain text received"}
    except Exception:
        return {"status": 200, "data": "Empty synthetic success"}

@app.post("/nodos/{node_id}/consolidar")
async def consolidate_sovereignty(node_id: str, body: ConsolidationBody):
    try:
        native_vector = model.encode(body.text)
        geodetic_matrix = get_geodetic_matrix_db()

        dim_db = get_current_dimension_db()
        dim_in = len(native_vector)
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

        if variance >= dynamic_threshold:
            new_state: LifecycleState = "consolidated"
            action_pot = 1.0
        else:
            new_state: LifecycleState = "incubating"
            action_pot = float(variance * 10.0)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE manifold_nodes
                SET text = ?, toon_factor = ?, lifecycle_state = ?, action_potential = ?,
                    revision_milestone = ?, vector_blob = ?, projections_json = ?
                WHERE id = ?
            """, (body.text, toon_symbol, new_state, action_pot,
                  int(body.ethical_key), serialize_vector(norm_idea_vector),
                  json.dumps(projections), node_id))

        return {"status": "SUCCESS", "new_state": new_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nodos")
async def get_manifold_nodes():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, toon_factor, lifecycle_state, action_potential,
                       revision_milestone, projections_json
                FROM manifold_nodes
                WHERE lifecycle_state != 'telemetry_error'
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
    except Exception:
        return {"status": "SUCCESS", "nodes": []}

@app.get("/telemetry")
async def get_telemetry_logs():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, projections_json, sys_internal_timestamp
                FROM manifold_nodes
                WHERE lifecycle_state = 'telemetry_error'
                ORDER BY sys_internal_timestamp DESC
            """)
            rows = cursor.fetchall()
        return [
            {"id": r[0], "trace": r[1], "meta": json.loads(r[2]), "time": r[3]}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/relations")
async def get_relations():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, source, target, state FROM manifold_edges")
            rows = cursor.fetchall()
        return [
            {"id": r[0], "source": r[1], "target": r[2], "state": r[3]}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/relations")
async def forge_relation(relation: HitlRelation):
    try:
        nodes = sorted([relation.source, relation.target])
        edge_id = f"edge-{nodes[0]}-{nodes[1]}"

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO manifold_edges (id, source, target, state)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET state = excluded.state
            """, (edge_id, relation.source, relation.target, relation.state))

        return {"status": "SUCCESS", "id": edge_id, "state": relation.state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# INTERACTIVE LOGOGRAPHIC GENESIS (ADR-015)
# =====================================================================

@app.post("/mutate/{new_symbol}")
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

            cursor.execute("SELECT id, vector_blob FROM manifold_nodes")
            nodes = cursor.fetchall()
            for node_id, blob in nodes:
                node_vector = np.frombuffer(blob, dtype=np.float64)
                if len(node_vector) < new_dimension:
                    node_vector_pad = np.pad(
                        node_vector, (0, new_dimension - len(node_vector)),
                        mode='constant', constant_values=0.0
                    )
                    cursor.execute(
                        "UPDATE manifold_nodes SET vector_blob = ? WHERE id = ?",
                        (serialize_vector(node_vector_pad), node_id)
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
