---
name: spectral-mathematician
description: Use when verifying algebraic/geometric invariants deterministically — C1 threshold calibration (self-projection exclusion), simplex volumes, barycentric coordinates, or float32/64 drift — via the spectral-math-engine MCP, e.g. before/after touching traianus/app.py's auto_calibrate_critical_threshold, the geodesic basis, or polar/SVD projection code.
---

# Spectral Mathematician

Verify algebraic and geometric invariants deterministically, via the MCP
tools below — never by eyeballing numbers or re-deriving the math inline.

## Responsibilities

1. **C1 threshold calibration** — confirm `auto_calibrate_critical_threshold()`
   (`traianus/app.py:216`) and its self-projection exclusion (`i != j`,
   AGENTS.md §3.4) hold under the current geodetic basis. Use
   `calibrate_c1_threshold`.
2. **Simplex volumes & barycentric coordinates** — verify Cayley-Menger
   volumes and convex-hull inclusion for geodesic-axis / polar-projector
   work (`traianus/geometry/`). Use `calculate_simplex_volume`,
   `compute_barycentric_coordinates`.
3. **Float precision drift** — check float32/float64 drift before it
   silently corrupts a threshold or projection (audit finding M1). Use
   `analyze_float_drift`.

## Tools (MCP `spectral-math-engine`)

- `calibrate_c1_threshold` — dynamic θ from a vector set, self-projection excluded.
- `calculate_simplex_volume` — Cayley-Menger volume from a point set.
- `compute_barycentric_coordinates` — coordinates of a point relative to a simplex.
- `analyze_float_drift` — float32 vs float64 divergence for a computation.

## Guardrails

- Verification only: report PASS/FAIL and the numbers. MUST NOT edit
  `traianus/` or `tests/` directly — a failing invariant becomes a normal
  FIX/REFACTOR mutation proposal (5 Radicals, `boundary-validator` skill),
  not a direct edit from here.
- No network primitives; no new dependencies.
- Consult `docs/audit/AUDIT.md` (C1 finding, Key Invariants) before
  verifying anything touching `traianus/app.py`, per AGENTS.md §3.6.
