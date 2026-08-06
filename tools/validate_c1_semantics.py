"""WP0 experiment (SPEC-REFACTOR-v0.2, Step 4): measure the real validity of
the Topological Key (sigma^2) over the Epoch 0 Seed on real data.

Falsifiable hypothesis (SPEC v0.2 section 2, M-c/M-d): sigma^2 >= theta_dyn
rewards non-flat spectral signatures. This tool:

  1. Builds the real Epoch 0 Seed (PROSTHETIC_NSM_V1) from the real
     all-MiniLM-L6-v2 model (offline, pinned revision).
  2. Measures the empirical sigma^2 distribution over the real corpus and
     compares it with theta_dyn (the C1 gate baseline).
  3. Asserts the dual-key Semantics (2.A) directly against
     evaluate_gate_v01 over a grid of spectra bracketing theta_dyn:
       - ethical_key=False        => NEVER consolidated, regardless of sigma^2
       - sigma^2 < theta_dyn      => NEVER consolidated, even with ethical_key=True
       - both keys satisfied      => consolidated (reachable, not degenerate)
  4. Exercises the real /consolidar path and re-asserts the C1 guard range.

Hermetic: writes only to an ephemeral SQLite file; no network.
"""

import os
import sys
import tempfile
import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from traianus import app as main_module
from traianus import bootstrap as gb
from traianus import storage as storage
from traianus.core import evaluate_gate_v01

CORPUS = [
    "Something happens.",
    "Someone.",
    "There is something here.",
    "Be in a place.",
    "One, two, and some more are part of the same collection.",
    "After a long time, before now, things were different.",
    "The cat sees the bird and hears it singing.",
    "Meeting on Tuesday at 10am to review the quarterly budget.",
    "The audit report confirms the documentation matches the code.",
    "I want to know if this is true.",
    "All the others agree with me now.",
    "I want to know if I can do something more with very little time.",
    "There is no one here right now.",
    "A very good and very big person lives very far from here.",
    "The distance between two places can be large or small.",
    "The ingestion process registers a note in the system deterministically.",
    "Move.",
]


def _variance(spec):
    mean = float(np.mean(spec))
    return float(np.mean((np.array(spec) - mean) ** 2))


def run():
    print("=== WP0: C1 SEMANTICS VALIDATION (Epoch 0 Seed, real data) ===")

    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    try:
        storage.DB_PATH = temp_db_path

        main_module.init_db()
        os.environ["HF_HUB_OFFLINE"] = "1"
        gb._model = main_module.get_model()
        gb.get_model = main_module.get_model
        gb.anchor_in_sqlite(gb.extract_pure_octagon())

        matrix = main_module.get_geodetic_matrix_db()
        theta = main_module.auto_calibrate_critical_threshold()
        print(f"-> Seed basis: {len(matrix)} axes ({main_module.MODEL_REVISION[:8]}...)")
        print(f"-> theta_dyn (C1 baseline, self-projection excluded): {theta:.6f}")

        # 2. Empirical sigma^2 distribution over the real corpus.
        spectra = []
        variances = []
        for text in CORPUS:
            native = main_module._encode_vector(text)
            projections = [
                float(np.dot(native, axis_entry["vector"])) for axis_entry in matrix.values()
            ]
            spectra.append(projections)
            variances.append(_variance(projections))

        variances = np.array(variances)
        print(f"-> Empirical sigma^2 over corpus (n={len(CORPUS)}):")
        print(f"     min={variances.min():.6f}  mean={variances.mean():.6f}  "
              f"max={variances.max():.6f}")
        print(f"     P50={np.percentile(variances, 50):.6f}  "
              f"P60={np.percentile(variances, 60):.6f}  "
              f"P90={np.percentile(variances, 90):.6f}")
        above = int((variances >= theta).sum())
        print(f"-> Corpus sigma^2 >= theta_dyn: {above}/{len(variances)} "
              f"({above / len(variances):.0%})")

        # 3. Semantics (2.A) grid: scaled real spectra bracket theta_dyn
        #    on both sides (variance scales with k^2 around its mean).
        grid = []
        for base in spectra:
            mean = float(np.mean(base))
            dev = np.array(base) - mean
            for k in (0.1, 0.5, 1.0, 2.0, 5.0, 10.0):
                grid.append((mean + k * dev).tolist())

        semantics_failures = []
        for spec in grid:
            v = _variance(spec)
            g_false = evaluate_gate_v01(spec, False, theta)
            g_true = evaluate_gate_v01(spec, True, theta)
            if g_false["state"] != "incubating":
                semantics_failures.append(("ethical_key=False consolidated", v))
            if v < theta and g_true["state"] != "incubating":
                semantics_failures.append(("sub-threshold consolidated", v))
            if v >= theta and g_true["state"] != "consolidated":
                semantics_failures.append(("super-threshold not consolidated", v))

        if semantics_failures:
            for kind, v in semantics_failures[:5]:
                print(f"   VIOLATION: {kind} at sigma^2={v:.6f}")
            raise AssertionError(
                f"Semantics (2.A) violated: {len(semantics_failures)}/{len(grid)} grid points"
            )
        print(f"-> Semantics (2.A) dual-key law: OK over {len(grid)} grid points "
              f"(sigma^2 in [0, {max(_variance(s) for s in grid):.4f}])")

        # 4. Real API reachability + C1 guard.
        client = TestClient(main_module.app)
        token = os.environ.setdefault("TRAIANUS_TOKEN", "dev-token-secret")
        headers = {"x-traianus-token": token}
        accepted = sum(
            client.post(
                "/ingesta", content=t.encode("utf-8"),
                headers={**headers, "Content-Type": "text/plain"},
            ).status_code == 200
            for t in CORPUS
        )
        nodes = client.get("/nodos", headers=headers).json().get("nodes", [])
        consolidated = sum(
            client.post(
                f"/nodos/{n['id']}/consolidar",
                json={"text": n["text"], "ethical_key": True},
                headers=headers,
            ).json().get("new_state") == "consolidated"
            for n in nodes
        )
        rate = consolidated / len(nodes) if nodes else 0.0
        print(f"-> API: {accepted}/{len(CORPUS)} accepted; consolidation rate "
              f"{rate:.0%} ({consolidated}/{len(nodes)})")
        # C1 guard: non-degenerate iff BOTH outcomes are observed (>= 1
        # consolidated AND >= 1 not). Exact count form of the old
        # `0.05 <= rate <= 0.95` bounds; no magic numbers.
        assert 1 <= consolidated <= len(nodes) - 1, (
            f"C1 gate degenerate: {consolidated}/{len(nodes)}"
        )
        print("-> C1 GUARD PASSED IN GREEN: non-degenerate (both outcomes observed)")
        print("✅ WP0 VALIDATION PASSED: sigma^2 is a working (falsifiable) hypothesis "
              "and the dual-key law holds on real data.")
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


if __name__ == "__main__":
    run()
