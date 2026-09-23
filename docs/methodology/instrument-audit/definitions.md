# Audit definitions

Shared by every instrument audit record in this directory. A reviewer reads this file and one
record file, nothing else under `frontend/`.

```
Audit definitions

Vectors      v ∈ S^383, L2-normalized. Corpus: the 2,221 Spinoza chunks frozen by
             tools/experiments/tooling/freeze_spinoza_embeddings.py (commit f26186d; output
             .data/spinoza_frozen, gitignored), float32 on disk, used as float64.
Basis        8 NSM geodetic axes a_1…a_8, tests/fixtures/nsm_axes_8.json (epoch
             PROSTHETIC_NSM_V1); â_k = a_k / ‖a_k‖. Stored in table geodesic_axes
             (traianus/storage/_storage.py:114); epochs: docs/architecture/ARCHITECTURE.md §7.
Operator     traianus/geometry/polar_projector.py, for anchor c₁ and poles c_A, c_B:
               ĉ₁ = c₁ / ‖c₁‖;  P⊥x = x − ⟨x, ĉ₁⟩ĉ₁                          (:235-237)
               v_dipole = P⊥c_A − P⊥c_B  (collinear fallback 2δ·u⊥)          (:184-188)
               r = P⊥(v − c₁)                                                (:279)
               λ = clip(⟨r, v_dipole⟩ / ‖v_dipole‖², −1, 1)                  (:283-285)
               d_esc = ‖r − λ·v_dipole‖                                      (:290)
             Since P⊥c₁ = 0 and v_dipole ⊥ ĉ₁ in both branches: r = P⊥v, ‖r‖² = 1 − y², and
             λ = clip(⟨v, v_dipole⟩ / ‖v_dipole‖², −1, 1).
λ_k          λ with c₁ = â of the rank-1 axis and (c_A, c_B) = â of the k-th dipole's two axes, as
             ranked by the record under review.
Position     x = λ₁, y = ⟨v, ĉ₁⟩.

Allowed reading   this file; derivations.md; contracts.md; the
                  record file under review; the files and lines cited in them.
Not allowed       frontend/POC.md; any other record's review history; docs/adrs/ADR-026-*;
                  traianus/geometry/spatial_observables.py (its docstring states prior results);
                  data/spinoza/telemetry/; docs/LEDGER.md; any manuscript.
```
