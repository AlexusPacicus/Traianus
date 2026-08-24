import os
import secrets
import hashlib
import re
from contextlib import asynccontextmanager
import numpy as np
import json
from typing import List, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from traianus.representation.sentence_transformer import (
    MODEL_ID,
    MODEL_REVISION,
    SentenceTransformerProvider,
)

from traianus.geometry.observables import (
    calibrate_critical_threshold,
    compute_kinetic_resistance,
)
from traianus.governance.gate import evaluate_gate
from traianus import storage
from traianus.config import resolve_epsilon_edge
from traianus.observability import (
    get_logger,
    generate_request_id,
    now_seconds,
)
from traianus.storage import (
    # Re-export shims (SPEC-M2-DELTA-0-1 Δ1): names referenced by the
    # harness/tools stay reachable as `traianus.app.X`. Only live callers are
    # re-exported; DB_PATH and persist_epsilon_edges are NOT (dead shims).
    init_db,
    get_geodetic_matrix_db,
)

# =====================================================================
# OFFLINE GUARD (audit M3): offline sovereignty. Model must be prefetched
# locally; no HF Hub downloads at runtime. First run is the only one that
# requires network (prefetch via bootstrap/setup). Enforced inside the
# representation provider module (`local_files_only=True`).
# =====================================================================
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def _startup_create_schema():
    """Creates the relational schema on the active DB_PATH at server boot.

    Import is side-effect free by design: `traianus.app` does NOT open a
    database or load the encoder at import time (hermeticity, L1). Both
    artifacts are created lazily — the schema on server startup, the encoder
    on first `get_provider()` call.
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

# Lazy provider (hermetic import, L1): the model is NOT built at import time.
# Import of `traianus.app` is side-effect free; `get_provider()` builds the
# representation provider on first use and caches it. Unit tests run with the
# deterministic mock provider injected (conftest `_hermetic_model`).
_provider = None


def get_provider():
    global _provider
    if _provider is None:
        _provider = SentenceTransformerProvider()
    return _provider

# =====================================================================
# SERVER-SIDE EPSILON FOR DETERMINISTIC E_n (ADR-023/H5, RE-09/CO-12)
# Epsilon is a server-side constant, never a client parameter (Zero-Trust).
# Configurable only at boot via TRAIANUS_EPSILON_EDGE; resolved through the
# central config module (single source of truth shared with audit tooling).
# =====================================================================
EPSILON_EDGE = resolve_epsilon_edge()

# =====================================================================
# ZERO-TRUST INGRESS PERIMETER (audit H2): ALLOWLIST.
# Everything that is not text/plain is rejected at the perimeter with 415.
# =====================================================================

ALLOWED_INGRESS_TYPES = {"text/plain"}

# /ingesta/vector label contract (node-id namespace protection): the label
# becomes part of persistent node ids and, downstream, edge ids.
_SAFE_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


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
# OFFICIAL PYDANTIC DATA CONTRACTS (CONTRACTS.md)
# =====================================================================

LifecycleState = Literal[
    "pending_approval",
    "consolidated",
    "incubating",
    "telemetry_error",
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

class VectorIngestBody(BaseModel):
    vector: list[float] = Field(..., description="Raw coordinate vector v ∈ R^d.")
    label: str | None = Field(default=None, description="Optional identifier or tag.")
    metadata: dict = Field(default_factory=dict, description="Optional metadata dictionary.")

# =====================================================================
# VECTOR UTILITIES
# =====================================================================

def serialize_vector(vector: np.ndarray) -> bytes:
    return vector.astype(np.float64).tobytes()

def _encode_vector(raw_text: str) -> np.ndarray:
    """Encodes and validates at the encoding boundary (SPEC v0.2 §3.4 P2).

    The binary invariant is verified on the NATIVE encoder output
    (text/plain -> vector), BEFORE normalization, padding, or float64
    serialization: 1-D, dimension == 384, dtype float32 (native model
    output), finite values, non-zero norm. A vector failing any check is
    rejected before it reaches manifold_nodes. Storage keeps the float64
    serialization (serialize_vector); this check is the only place the
    native float32 dtype is observable.
    """
    provider = get_provider()
    native_vector = provider.encode(raw_text)
    if not isinstance(native_vector, np.ndarray) or native_vector.ndim != 1:
        raise ValueError("Provider output must be a 1-D vector.")
    if native_vector.dtype != np.float32:
        raise ValueError(
            f"Provider output dtype {native_vector.dtype} != float32 (native model dtype)."
        )
    if native_vector.size != provider.dimension:
        raise ValueError(
            f"Provider dimension {native_vector.size} != {provider.dimension} "
            "(ingress binary invariant)."
        )
    if not np.all(np.isfinite(native_vector)):
        raise ValueError("Provider output contains non-finite values.")
    if np.linalg.norm(native_vector) == 0.0:
        raise ValueError("Provider output has zero norm.")
    return native_vector

def auto_calibrate_critical_threshold() -> float:
    """C1 coordinator: reads the active geodetic basis and calibrates the
    dynamic threshold excluding self-projection (audit C1)."""
    matrix = get_geodetic_matrix_db()
    if not matrix:
        raise RuntimeError("[Traianus Core] Error: Geodetic matrix empty. Aborting autocalibration.")
    vectors = [entry["vector"] for entry in matrix.values()]
    return calibrate_critical_threshold(vectors)

# =====================================================================
# ASYNCHRONOUS GEOMETRIC ROUTING
# =====================================================================

def async_spectral_processor(ingestion_id: int, raw_text: str):
    try:
        native_vector = _encode_vector(raw_text)
        geodetic_matrix = get_geodetic_matrix_db()
        if not geodetic_matrix:
            raise RuntimeError(
                "[Traianus Core] Critical infrastructure failure: geodetic_axes table is empty. "
                "Run `traianus-bootstrap` (traianus.bootstrap:main) to bootstrap the geodetic baseline before ingestion."
            )

        dim_db = storage.get_current_dimension_db()
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

        with storage.get_db_connection() as conn:
            # Node revision + queue-status update commit atomically: a queue
            # failure rolls back the node revision (single transaction).
            storage.insert_node_revision(
                f"NODE_{ingestion_id}",
                raw_text,
                toon_symbol,
                validated_entity.lifecycle_state,
                action_potential,
                int(validated_entity.revision_milestone),
                serialize_vector(norm_idea_vector),
                projections_json,
                storage.active_epoch(),
                conn=conn,
            )
            storage.mark_queue_processed(conn, ingestion_id)

        get_logger(request_id=f"bg-{ingestion_id}").info(
            "ingestion_processed", variance=round(variance, 6)
        )

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        try:
            storage.insert_error_log(
                f"LOG_{ingestion_id}",
                f"[ValidationError / StructuralDrift] ingestion_id={ingestion_id}\n\n{error_trace}",
                "▱",
                0.0,
                0,
                b"",
                json.dumps({"error": str(e)}),
            )
        except Exception:
            pass

# =====================================================================
# FRONTEND CUSTOMS OPERATIONAL ENDPOINTS
# =====================================================================

@app.post("/ingesta", dependencies=[Depends(require_token)])
async def frontend_ingestion_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    x_idempotency_key: str | None = Header(default=None),
):
    # Zero-Trust ingress allowlist (H2): the MIME check moved from the JSON
    # `type` field to the Content-Type header (SPEC v0.2 §3.4, contract change).
    content_type = request.headers.get("content-type", "").split(";")[0].strip()
    if content_type not in ALLOWED_INGRESS_TYPES:
        raise HTTPException(status_code=415, detail="Only text/plain is accepted at ingress.")
    # Byte-level verification (SEC-a / §3.4 P1): null-byte scan + strict UTF-8.
    raw_bytes = await request.body()
    if b"\x00" in raw_bytes:
        raise HTTPException(status_code=400, detail="Invalid binary payload (null byte detected).")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 payload.") from e
    try:
        ingestion_id, duplicate = storage.enqueue_ingest(text, x_idempotency_key)
    except storage.StorageError as e:
        raise HTTPException(status_code=503, detail="Ingress persistence unavailable.") from e
    if duplicate:
        return {"status": "accepted", "ingestion_id": ingestion_id, "duplicate": True}
    background_tasks.add_task(async_spectral_processor, ingestion_id, text)
    return {"status": "accepted", "ingestion_id": ingestion_id}

@app.post("/ingesta/vector", status_code=201, dependencies=[Depends(require_token)])
async def vector_ingestion_endpoint(body: VectorIngestBody, request: Request, response: Response):
    """Provider-agnostic vector ingestion (RH-1): accepts raw coordinate
    arrays without text conversion, text/plain headers, or language encoders.

    Validates dimension, numeric integrity, and non-zero norm; L2-normalizes
    before projection; persists as append-only node revision.

    Emits structured logs (JSON) with request_id for observability.
    Propagates X-Request-ID for distributed tracing correlation."""
    t_start = now_seconds()
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    log = get_logger(request_id=request_id)

    log.info(
        "vector_ingestion_start",
        label=body.label,
        vector_dim=len(body.vector),
        has_metadata=bool(body.metadata),
    )

    geodetic_matrix = get_geodetic_matrix_db()
    if not geodetic_matrix:
        log.error("vector_ingestion_failed", phase="ingress", reason="basis_uninitialized")
        raise HTTPException(
            status_code=400,
            detail=(
                "Geodetic basis not initialized. "
                "Run `traianus-bootstrap` (traianus.bootstrap:main) before ingestion."
            ),
        )

    dim_db = storage.get_current_dimension_db()
    raw_vector = body.vector

    if len(raw_vector) == 0 or len(raw_vector) != dim_db:
        log.warning("vector_ingestion_rejected", phase="validation", reason="dimension_mismatch",
                     got=len(raw_vector), expected=dim_db)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Vector dimension {len(raw_vector)} does not match geodetic baseline "
                f"{dim_db}; dimension mismatch rejected (I-6.2/L6)."
            ),
        )

    for idx, val in enumerate(raw_vector):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            log.warning("vector_ingestion_rejected", phase="validation", reason="non_numeric",
                         index=idx, type=type(val).__name__)
            raise HTTPException(
                status_code=422,
                detail=f"Vector element at index {idx} is not numeric (type {type(val).__name__}).",
            )

    arr = np.array(raw_vector, dtype=np.float64)

    if not np.all(np.isfinite(arr)):
        log.warning("vector_ingestion_rejected", phase="validation", reason="non_finite")
        raise HTTPException(
            status_code=422,
            detail="Vector contains non-finite values (NaN or Inf).",
        )

    norm = np.linalg.norm(arr)
    if norm == 0.0:
        log.warning("vector_ingestion_rejected", phase="validation", reason="zero_vector")
        raise HTTPException(status_code=422, detail="Zero-vector (norm == 0) rejected.")

    norm_idea_vector = arr / norm

    t_proj_start = now_seconds()
    projections = {}
    for axis_id, axis_entry in geodetic_matrix.items():
        projections[axis_id] = float(np.dot(norm_idea_vector, axis_entry["vector"]))

    dominant_attractor = max(
        geodetic_matrix.keys(),
        key=lambda k: np.dot(norm_idea_vector, geodetic_matrix[k]["vector"]),
    )
    toon_symbol = geodetic_matrix[dominant_attractor]["symbol"]

    dynamic_threshold = auto_calibrate_critical_threshold()

    gate = evaluate_gate(
        list(projections.values()), ethical_key=False, threshold=dynamic_threshold
    )
    lifecycle_state: LifecycleState = gate["state"]
    action_potential = float(gate["topological_key"]["variance"])


    projections_json = json.dumps({
        axis_id: float(value)
        for axis_id, value in projections.items()
    })

    if body.label and not _SAFE_LABEL_RE.fullmatch(body.label):
        log.warning("vector_ingestion_rejected", phase="validation", reason="unsafe_label")
        raise HTTPException(
            status_code=422,
            detail=(
                "Label must match [A-Za-z0-9_-]{1,64} "
                "(node-id namespace protection)."
            ),
        )

    if body.label:
        node_id = f"VEC_{body.label}"
    else:
        digest = hashlib.sha256(serialize_vector(norm_idea_vector)).hexdigest()[:12]
        node_id = f"VEC_{digest}"

    try:
        with storage.get_db_connection() as conn:
            seq = storage.insert_node_revision(
                node_id,
                body.label or "",
                toon_symbol,
                lifecycle_state,
                action_potential,
                0,
                serialize_vector(norm_idea_vector),
                projections_json,
                storage.active_epoch(),
                conn=conn,
            )
    except storage.StorageError as e:
        log.error("vector_ingestion_failed", phase="persist", reason="storage_error")
        raise HTTPException(status_code=503, detail="Ingress persistence unavailable.") from e

    # L1 (audit): retrieve previous vector revision for K_cin computation.
    # Append-only log: current revision is seq; previous is the next lower seq.
    prev_vector = None
    with storage.get_db_connection() as conn:
        prev_row = conn.execute(
            "SELECT vector_blob FROM manifold_nodes WHERE id = ? AND seq < ? ORDER BY seq DESC LIMIT 1",
            (node_id, seq),
        ).fetchone()
        if prev_row is not None:
            prev_vector = np.frombuffer(prev_row[0], dtype=np.float64)

    # Compute kinematic resistance K_cin if previous vector exists.
    k_cin = None
    if prev_vector is not None:
        geodetic_matrix = get_geodetic_matrix_db()
        if geodetic_matrix:
            B_0 = np.vstack([axis_entry["vector"] for axis_entry in geodetic_matrix.values()])
            k_cin = float(compute_kinetic_resistance(norm_idea_vector, prev_vector, B_0))

    duration = now_seconds() - t_start

    log.info(
        "vector_ingestion_completed",
        phase="complete",
        node_id=node_id,
        seq=seq,
        lifecycle_state=lifecycle_state,
        spectral_variance=gate["topological_key"]["variance"],
        k_cin=k_cin,
        duration_ms=round(duration * 1000, 2),
        gate_passed=gate["topological_key"]["passed"],
    )

    response.headers["X-Request-ID"] = request_id

    return {
        "status": "accepted",
        "node_id": node_id,
        "seq": seq,
        "lifecycle_state": lifecycle_state,
        "spectral_variance": float(gate["topological_key"]["variance"]),
        "k_cin": k_cin,
        "projections": projections,
        "dual_key_status": {
            "topological_key": gate["topological_key"],
            "ethical_key": gate["ethical_key"],
            "consolidated": gate["state"] == "consolidated",
        },
    }

@app.post("/nodos/{node_id}/consolidar", dependencies=[Depends(require_token)])
async def consolidate_sovereignty(node_id: str, body: ConsolidationBody):
    try:
        native_vector = _encode_vector(body.text)
        geodetic_matrix = get_geodetic_matrix_db()
        if not geodetic_matrix:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Geodetic basis not initialized. "
                    "Run `traianus-bootstrap` (traianus.bootstrap:main) before consolidation."
                ),
            )

        dim_db = storage.get_current_dimension_db()
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

        dynamic_threshold = auto_calibrate_critical_threshold()

        dominant_attractor = max(
            geodetic_matrix.keys(),
            key=lambda k: np.dot(norm_idea_vector, geodetic_matrix[k]["vector"]),
        )
        toon_symbol = geodetic_matrix[dominant_attractor]["symbol"]

        # Dual-Key Consolidation (ADR-022, SPEC v0.2 §3.2): the pure kernel is
        # the single authority for the decision. The Topological Key acts as a
        # provisional informational geometric score; consolidation requires BOTH
        # keys simultaneously (AND). Neither acts alone.
        gate = evaluate_gate(
            list(projections.values()), body.ethical_key, dynamic_threshold
        )
        new_state: LifecycleState = gate["state"]
        action_pot = 1.0 if new_state == "consolidated" else float(gate["topological_key"]["variance"])
        revision_milestone_val = 1 if body.ethical_key else 0

        with storage.get_db_connection() as conn:
            # H4: consolidation INSERTS a new revision with increasing seq;
            # never overwrites the original row (UPDATE was prohibited).
            if not storage.node_exists(conn, node_id):
                raise HTTPException(status_code=404, detail=f"Node {node_id} not found.")
            storage.insert_node_revision(
                node_id, body.text, toon_symbol, new_state, action_pot,
                revision_milestone_val,
                serialize_vector(norm_idea_vector), json.dumps(projections),
                storage.active_epoch(),
                conn=conn,
            )

            # SPEC v0.2 §3.3 (M-a): E_n is a purely observational artifact.
            # It is NOT written from the consolidation transaction; /relations
            # computes the deterministic ε-adjacency on read.

        return {
            "status": "SUCCESS",
            "new_state": new_state,
            "dual_key_status": {
                "topological_key": gate["topological_key"],
                "ethical_key": gate["ethical_key"],
                "consolidated": new_state == "consolidated",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.get("/nodos")
async def get_manifold_nodes():
    try:
        rows = storage.get_current_nodes()

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
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.get("/telemetry", dependencies=[Depends(require_token)])
async def get_telemetry_logs():
    try:
        rows = storage.get_telemetry_errors()
        return [
            {"id": r[0], "trace": r[1], "meta": json.loads(r[2]), "time": r[3]}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.get("/relations", dependencies=[Depends(require_token)])
async def get_relations():
    try:
        rows = storage.get_current_edges()
        manual = [
            {"id": r[0], "source": r[1], "target": r[2], "state": r[3]}
            for r in rows
        ]
        auto = [
            {
                "id": f"auto-edge-{e['source']}-{e['target']}",
                "source": e["source"],
                "target": e["target"],
                "state": "auto",
            }
            for e in storage.rebuild_epsilon_edges(EPSILON_EDGE)
        ]
        return sorted(manual + auto, key=lambda r: r["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post("/relations", dependencies=[Depends(require_token)])
async def forge_relation(relation: HitlRelation):
    try:
        nodes = sorted([relation.source, relation.target])
        edge_id = f"edge-{nodes[0]}-{nodes[1]}"

        with storage.get_db_connection() as conn:
            # L2 (audit): dangling edges not allowed. Each endpoint
            # must exist as a node in manifold_nodes; if not, 4xx (404).
            for endpoint in (relation.source, relation.target):
                if not storage.node_exists(conn, endpoint):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Node {endpoint} not found. Dangling edge rejected (L2).",
                    )
            # H4: edges are an append-only revision log. Re-forging an edge
            # INSERTS a new revision with increasing seq; the previous one is
            # never overwritten (no UPDATE / ON CONFLICT DO UPDATE).
            storage.insert_edge_revision(
                conn, edge_id, relation.source, relation.target, relation.state
            )

        return {"status": "SUCCESS", "id": edge_id, "state": relation.state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.") from e

# =====================================================================
# INTERACTIVE LOGOGRAPHIC GENESIS (ADR-015)
# =====================================================================

@app.post("/mutate/{new_symbol}", dependencies=[Depends(require_token)])
async def logographic_genesis(new_symbol: str):
    try:
        current_axes = storage.get_active_epoch_axes()
        if not current_axes:
            raise HTTPException(status_code=400, detail="Geodetic baseline not initialized.")

        sample_vector = np.frombuffer(current_axes[0][3], dtype=np.float64)
        current_dimension = len(sample_vector)
        new_dimension = current_dimension + 1

        # Epoch-append (SPEC v0.2 §3.3, M-a): never UPDATE existing rows.
        # A COMPLETE new basis (re-padded axes + canonical axis) is inserted
        # under a fresh epoch_provenance; the previous epoch stays immutable.
        active = storage.active_epoch()
        epoch_num = int(active.rsplit("_V", 1)[-1])
        new_epoch = f"PROSTHETIC_NSM_V{epoch_num + 1}"

        with storage.get_db_connection() as conn:
            for axis_id, symbol, tag, blob in current_axes:
                axis_vector = np.frombuffer(blob, dtype=np.float64)
                axis_vector_pad = np.pad(axis_vector, (0, 1), mode='constant', constant_values=0.0)
                storage.insert_axis(
                    conn, axis_id, symbol, tag,
                    serialize_vector(axis_vector_pad), new_epoch,
                )

            new_axis = np.zeros(new_dimension)
            new_axis[-1] = 1.0
            new_id = f"T{len(current_axes) + 1}"
            storage.insert_axis(
                conn, new_id, new_symbol, "_CUSTOM",
                serialize_vector(new_axis), new_epoch,
            )

        return {
            "status": "SUCCESS",
            "message": f"Logographic Genesis completed. Hyperspace expanded to {new_dimension}D.",
            "new_epoch": new_epoch,
            "new_axis": f"{new_symbol}_CUSTOM",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.") from e
