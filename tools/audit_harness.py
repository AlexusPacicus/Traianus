import os
import sys
import tempfile
import sqlite3
import numpy as np
from fastapi.testclient import TestClient

# Ensure traianus package import
sys.path.insert(0, os.path.abspath("."))

from traianus import app as main_module
from traianus import bootstrap as gb

def run_audit():
    print("=== TRAIANUS EMPIRICAL AUDIT HARNESS (REPAIRED) ===")
    
    # 1. Hermetic Database Isolation
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    
    main_module.DB_PATH = temp_db_path
    gb.DB_PATH = temp_db_path
    
    # Initialize tables and geodetic baseline
    main_module.init_db()
    os.environ["HF_HUB_OFFLINE"] = "1"
    gb.model = main_module.model
    gb.anchor_in_sqlite(gb.extract_pure_octagon())

    mtx = main_module.get_geodetic_matrix_db()
    vecs = [e["vector"] for e in mtx.values()]

    # 2. Measure basis orthogonality
    M = np.stack(vecs)
    G = M @ M.T
    off = G[~np.eye(len(M), dtype=bool)]
    print(f"-> Basis orthogonality (off-diagonal cosine) - Mean: {off.mean():.4f}, Max: {off.max():.4f}")

    client = TestClient(main_module.app)
    
    # 3. Diversified Corpus (calibrated against the corrected C1 threshold):
    #    6 high-contrast notes written in NSM primitives (variance >>
    #    threshold 0.004292) and 14 low-contrast thematic/narrative notes
    #    (variance << threshold). Expected rate ~30% (ideal [10%, 40%], within
    #    the gate [5%, 95%]) — C1 regression guard.
    corpus = [
        # --- High contrast with a geodetic axis (expected: PASS) ---
        "Something happens.",
        "Someone.",
        "There is something here.",
        "Be in a place.",
        "One, two, and some more are part of the same collection.",
        "After a long time, before now, things were different.",
        # --- Varied low-contrast thematic notes (expected: FAIL) ---
        "The cat sees the bird and hears it singing.",
        "Meeting on Tuesday at 10am to review the quarterly budget.",
        "The audit report confirms the documentation matches the code.",
        "I want to know if this is true.",
        "All the others agree with me now.",
        "The cat sees the bird and hears it singing.",
        "The audit report confirms the documentation matches the code.",
        "Meeting on Tuesday at 10am to review the quarterly budget.",
        "I want to know if I can do something more with very little time.",
        "There is no one here right now.",
        "A very good and very big person lives very far from here.",
        "The distance between two places can be large or small.",
        "The ingestion process registers a note in the system deterministically.",
        "Move.",
    ]
    
    token = os.environ.get("TRAIANUS_TOKEN", "dev-token-secret")
    # H3 fail-closed: if TRAIANUS_TOKEN is not in the environment, require_token
    # expects "" and every protected route responds 401. The harness propagates
    # its default token to the environment so both parties share the same secret.
    os.environ.setdefault("TRAIANUS_TOKEN", token)
    headers = {"x-traianus-token": token}
    
    # 4. Authenticated ingestion
    accepted_count = 0
    for t in corpus:
        res = client.post("/ingesta", json={"type": "text/plain", "text": t}, headers=headers)
        if res.status_code == 200:
            accepted_count += 1

    print(f"-> Notes accepted at ingestion (H1/H2/H3): {accepted_count}/{len(corpus)}")

    # 5. Get nodes
    res = client.get("/nodos", headers=headers).json()
    nodes = res.get("nodes", [])

    # 6. Evaluate Consolidation (Topological Key + Ethical Key)
    consolidated = 0
    for n in nodes:
        resp = client.post(
            f"/nodos/{n['id']}/consolidar",
            json={"text": n["text"], "ethical_key": True},
            headers=headers
        ).json()
        if resp.get("new_state") == "consolidated":
            consolidated += 1

    rate = consolidated / len(nodes) if nodes else 0.0
    print(f"-> Measured consolidation rate: {rate:.0%} ({consolidated}/{len(nodes)})")
    
    # Cleanup temp file
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

    # C1 Regression Guard
    assert 0.05 <= rate <= 0.95, f"❌ CONSOLIDATION GATE DEGENERATE: {rate:.0%} (See Audit C1)"
    print("✅ C1 GUARD PASSED IN GREEN: Rate within operational range [5%, 95%]")

if __name__ == "__main__":
    run_audit()
