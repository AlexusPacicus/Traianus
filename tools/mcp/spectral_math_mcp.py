import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import uuid
import math
import numpy as np

from traianus.geometry.observables import (
    calibrate_critical_threshold as _kernel_calibrate_critical_threshold,
)

# ---------------------------------------------------------------------------
# Core Deterministic Math Functions (Executed in compiled NumPy/math)
# ---------------------------------------------------------------------------

def calibrate_c1_threshold(matrix_rows: list[list[float]]) -> dict:
    """
    Calibrates the critical variance threshold on S^{d-1} excluding self-projection (i == j).
    Mitigates variance inflation (Correction C1 / Audit finding C1).
    """
    vectors = [np.array(row, dtype=np.float64) for row in matrix_rows]
    # L2-normalize vectors onto S^{d-1}
    normalized = []
    for v in vectors:
        norm = np.linalg.norm(v)
        normalized.append(v / norm if norm > 0 else v)



    matrix = np.stack(normalized) if normalized else np.zeros((0, 0))
    # Invariant-critical variance math is delegated to the canonical kernel
    # (traianus.geometry.observables); this layer keeps presentation only.
    critical_threshold = (
        _kernel_calibrate_critical_threshold(list(matrix)) if len(matrix) else 0.0
    )
    sims = matrix @ matrix.T if len(matrix) else np.zeros((0, 0))
    off_diagonals = sims[~np.eye(len(matrix), dtype=bool)] if len(matrix) else []
    mean_off_diag = float(np.mean(off_diagonals)) if len(off_diagonals) else 0.0
    max_off_diag = float(np.max(off_diagonals)) if len(off_diagonals) else 0.0

    return {
        "status": "SUCCESS",
        "critical_threshold": critical_threshold,
        "mean_off_diagonal_cosine": mean_off_diag,
        "max_off_diagonal_cosine": max_off_diag,
        "evaluated_axes_count": len(normalized),
    }


def calculate_simplex_volume(vertices_rows: list[list[float]]) -> dict:
    """
    Calculates the exact volume of a k-simplex (e.g. tetrahedron for k=3)
    embedded in R^d using the Cayley-Menger Determinant.
    """
    V = np.array(vertices_rows, dtype=np.float64)
    num_vertices, d = V.shape
    k = num_vertices - 1  # dimension of the simplex

    if num_vertices < 2:
        return {"status": "ERROR", "reason": "A simplex requires at least 2 vertices."}

    # Distance squared matrix D
    D = np.zeros((num_vertices, num_vertices), dtype=np.float64)
    for i in range(num_vertices):
        for j in range(num_vertices):
            diff = V[i] - V[j]
            D[i, j] = np.dot(diff, diff)

    # Build Cayley-Menger matrix B of size (k+2) x (k+2)
    B = np.zeros((num_vertices + 1, num_vertices + 1), dtype=np.float64)
    B[0, 1:] = 1.0
    B[1:, 0] = 1.0
    B[1:, 1:] = D

    det_B = float(np.linalg.det(B))
    
    # Formula: Vol^2 = (-1)^(k+1) / ( 2^k * (k!)^2 ) * det(B)
    factor = ((-1) ** (k + 1)) / ((2 ** k) * (math.factorial(k) ** 2))
    vol_sq = factor * det_B
    vol = float(math.sqrt(max(0.0, vol_sq)))

    return {
        "status": "SUCCESS",
        "simplex_dimension_k": k,
        "embedding_dimension_d": d,
        "cayley_menger_det": det_B,
        "volume": vol,
    }


def compute_barycentric_coordinates(
    point_row: list[float], simplex_vertices_rows: list[list[float]]
) -> dict:
    """
    Computes barycentric coordinates of a point relative to a k-simplex.
    Verifies if the point lies inside the convex hull (all lambda_i >= 0).
    """
    P = np.array(point_row, dtype=np.float64)
    V = np.array(simplex_vertices_rows, dtype=np.float64)
    num_vertices, d = V.shape
    k = num_vertices - 1

    # Linear system: sum_{i=1}^k lambda_i * (V_i - V_0) = P - V_0
    V0 = V[0]
    A = (V[1:] - V0).T  # shape (d, k)
    b = P - V0           # shape (d,)

    # Solve least squares for over/under-determined systems
    lambda_1_to_k, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
    lambda_0 = 1.0 - float(np.sum(lambda_1_to_k))
    
    coords = [lambda_0] + [float(x) for x in lambda_1_to_k]
    is_inside = all(c >= -1e-7 for c in coords)  # small epsilon for floating point tolerance

    return {
        "status": "SUCCESS",
        "barycentric_coordinates": coords,
        "is_inside_convex_hull": is_inside,
        "reconstruction_residual": float(residuals[0]) if len(residuals) > 0 else 0.0,
    }


def analyze_float_drift(vector_raw: list[float]) -> dict:
    """
    Measures precision drift when converting between float32 (PyTorch default)
    and float64 (SQLite storage default). Addresses Issue M1.
    """
    v_raw = np.array(vector_raw, dtype=np.float64)
    v_32 = v_raw.astype(np.float32)
    v_64_from_32 = v_32.astype(np.float64)

    # Chebyshev distance (L_infinity)
    chebyshev_dist = float(np.max(np.abs(v_raw - v_64_from_32)))
    
    # L2 norm difference
    l2_diff = float(np.linalg.norm(v_raw - v_64_from_32))

    # Cosine similarity between original and float32 truncated
    norm_raw = np.linalg.norm(v_raw)
    norm_32 = np.linalg.norm(v_64_from_32)
    
    if norm_raw > 0 and norm_32 > 0:
        cosine_sim = float(np.dot(v_raw, v_64_from_32) / (norm_raw * norm_32))
    else:
        cosine_sim = 1.0

    return {
        "status": "SUCCESS",
        "chebyshev_distance": chebyshev_dist,
        "l2_norm_diff": l2_diff,
        "cosine_similarity": cosine_sim,
        "significant_drift_detected": chebyshev_dist > 1e-6,
    }


# ---------------------------------------------------------------------------
# MCP Server (Model Context Protocol) over stdio (JSON-RPC 2.0)
# ---------------------------------------------------------------------------

SERVER_NAME = "spectral-math-engine"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS_LIST = [
    {
        "name": "calibrate_c1_threshold",
        "description": "Calculates the critical variance threshold on S^{d-1} excluding self-projections (i == j).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "matrix": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "Basis matrix (k x d) as a list of coordinate vectors.",
                }
            },
            "required": ["matrix"],
        },
    },
    {
        "name": "calculate_simplex_volume",
        "description": "Calculates exact k-simplex volume via Cayley-Menger Determinant.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vertices": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "Simplex vertices ((k+1) x d) as a list of coordinate vectors.",
                }
            },
            "required": ["vertices"],
        },
    },
    {
        "name": "compute_barycentric_coordinates",
        "description": "Computes barycentric coordinates and tests convex hull inclusion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Target point coordinates in R^d.",
                },
                "simplex_vertices": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "Simplex vertices ((k+1) x d).",
                },
            },
            "required": ["point", "simplex_vertices"],
        },
    },
    {
        "name": "analyze_float_drift",
        "description": "Measures Chebyshev and L2 precision drift between float32 and float64 representations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vector": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Raw coordinate vector to analyze.",
                }
            },
            "required": ["vector"],
        },
    },
]


def _rpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(req: dict):
    request_id = req.get("id")
    if request_id is None:
        return None

    method = req.get("method")

    if method == "initialize":
        params = req.get("params") or {}
        return _rpc_result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Spectral Math Engine: deterministic algebraic & geometric computation.",
                "_client": params.get("clientInfo", {}),
            },
        )

    if method == "ping":
        return _rpc_result(request_id, {})

    if method == "tools/list":
        return _rpc_result(request_id, {"tools": TOOLS_LIST})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}

        try:
            # Validate required arguments per inputSchema before dispatch.
            REQUIRED_ARGS = {
                "calibrate_c1_threshold": ["matrix"],
                "calculate_simplex_volume": ["vertices"],
                "compute_barycentric_coordinates": ["point", "simplex_vertices"],
                "analyze_float_drift": ["vector"],
            }
            if name is None:
                return _rpc_error(request_id, -32602, "Missing tool name")
            required = REQUIRED_ARGS.get(name)
            if required is None:
                return _rpc_error(request_id, -32602, f"Unknown tool: {name!r}")
            missing = [k for k in required if k not in args]
            if missing:
                return _rpc_error(request_id, -32602, f"Missing required args: {missing}")

            if name == "calibrate_c1_threshold":
                res = calibrate_c1_threshold(args["matrix"])
            elif name == "calculate_simplex_volume":
                res = calculate_simplex_volume(args["vertices"])
            elif name == "compute_barycentric_coordinates":
                res = compute_barycentric_coordinates(
                    args["point"], args["simplex_vertices"]
                )
            elif name == "analyze_float_drift":
                res = analyze_float_drift(args["vector"])

            is_error = res.get("status") == "ERROR" if isinstance(res, dict) else False
            return _rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2)}],
                    "isError": is_error,
                },
            )
        except Exception as e:
            return _rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps({"status": "ERROR", "reason": str(e)})}],
                    "isError": True,
                },
            )

    return _rpc_error(request_id, -32601, f"Method not found: {method}")


def main():
    """Main MCP stdio server loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[{SERVER_NAME}] invalid JSON-RPC: {e}\n")
            sys.stderr.flush()
            continue

        if not isinstance(request, dict):
            sys.stderr.write(f"[{SERVER_NAME}] invalid JSON-RPC: not an object\n")
            sys.stderr.flush()
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()