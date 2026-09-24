# Contracts

The mathematical and data contract of each measurement: exact input, exact output, the function
between them, and the bit-level data engineering that makes code and contract comparable. Records
(`K6.md`, `R4.md`) describe the instrument; this file states what it computes. Shortcuts are
proved in `derivations.md` and verified by `tests/unit/test_audit_derivations.py`.

Language: the formal parts are mathematics and data layout; each "En palabras" line is in
Spanish by the author's decision — a declared exception to AUDIT L3 for these translations only.

## 0. Data layer, bit level (shared)

```
Artefacts (inputs)
  embeddings.npy   NPY v1.0; header {'descr': '<f4', 'fortran_order': False, 'shape': (2221, 384)};
                   IEEE-754 binary32, little-endian, C order.
                   sha256 eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1.
                   Built by tools/experiments/tooling/freeze_spinoza_embeddings.py (`embed`):
                   encoder output (batched) cast to binary64, normalised in binary64
                   (raw / ‖raw‖), then rounded to binary32 and stored (corrected 2026-09-24: this
                   line said the normalisation ran in binary32).
  labels.json      UTF-8 JSON array of 2,221 {"label", "part"} objects, row order = embeddings rows.
                   sha256 1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f.
  nsm_axes_8.json  tests/fixtures; UTF-8 JSON array of 8 {"id", "simbolo", "tag", "vector"}, vector =
                   384 decimal literals, parsed by json into binary64 (correctly rounded).
                   sha256 b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35.
  Every script reads each artefact once, computes its sha256 on those bytes and parses the same
  bytes (amended 2026-09-19); it refuses to run on a mismatch.

Integrity: no nulls in, no silent bit flips
  Null elimination, after the digest check and before any computation; any violation stops the
  run with the row or key named:
    every value finite (no NaN, no ±Inf); every row's ‖v‖ within 3e-5 of 1 (a binary32
    normalisation over d = 384 terms errs by at most ≈ d·2⁻²⁴ ≈ 2.3e-5; the artefact's rows,
    normalised in binary64 and then rounded to binary32, err by at most ≈ 2⁻²⁴ ≈ 6e-8, so the
    bound holds with room, corrected 2026-09-24); no JSON null, empty or
    duplicate label; every "part" present, non-null and non-empty (declared: checked although K6
    does not read it); label count = row count; 8 axes with unique ids, each 384 finite values,
    ‖a_k‖ > 0 (amended 2026-09-19).
  Bit flips — each layer must catch what it can, and the tests prove it by flipping one bit:
    file layer: any single bit flipped in any input artefact or consumed result changes its
      sha256, and the script refuses to run (test: flip bits at the header, the first and the
      last data byte, and a random position of each file; every one must be refused);
    memory layer (amended 2026-09-19): a flipped exponent bit multiplies a component v_i by a
      power of two, and null elimination catches it only when ‖v‖ leaves 1 ± 3e-5:
      exponent MSB: |v_i| becomes ≥ 2, so ‖v‖ ≥ 2; always rejected (test: a random component);
      exponent LSB (amended 2026-09-19): a normal v_i doubles or halves, ‖v‖² changes by +3v_i²
        or −¾v_i²; rejected only above |v_i| ≈ 4.5e-3 (doubling) or ≈ 8.9e-3 (halving), smaller
        components pass (tests: components above and below the derived magnitude, both
        outcomes asserted); a zero or subnormal v_i (exponent field 0) becomes a small normal,
        |v_i| ∈ [2⁻¹²⁶, 2⁻¹²⁵), far below the threshold, and passes (test: 0 and 2⁻¹⁴⁰);
      mantissa bit k, 1 ≤ k ≤ 22 (amended 2026-09-19): changes |v_i| by a relative r ≤ 2^(k−23)
        (≤ 2⁻¹ at k = 22); from ‖v‖ = 1, ‖v‖² moves by at most v_i²(2r + r²), so the flip can be
        caught only if |v_i| ≥ √((1 − (1 − 3e-5)²) / (2r + r²)) — a derived bound, necessary, not
        sufficient: ≈ 6.9e-3 at k = 22, ≈ 0.99 at k = 8, > 1 for k ≤ 7 (never caught). Only
        high mantissa bits of large components are caught (tests: bit 22 below the bound
        passes; well above it, where r > 1/4 moves ‖v‖² by ≥ 0.4375·v_i², it is refused);
    declared blind spots, seen only by the file digest (tests: the flip passes validation —
      documenting the limit, not hiding it):
      sign bit: ‖v‖ is unchanged exactly; no norm check can see it;
      mantissa bit 0: changes one component by ≈ 1e-7, inside binary32 rounding (bits 1–7 are
        blind as well, by the bound above).

Conversions
  V64 = V32.astype('<f8')                       exact: every binary32 is a binary64.
  v̂ = v / np.sqrt(v @ v), row by row, binary64  re-normalisation; bits depend on the dot's
                                                  summation order (see Determinism).
  â_k = a_k / np.sqrt(a_k @ a_k), binary64.

Engine path (what the map is drawn from), for comparison
  provider output binary32 (one text at a time) → ‖·‖ and division in binary32 →
  .astype(np.float64).tobytes() → SQLite BLOB of 384 × 8 bytes, native byte order ('<f8' on
  x86-64 and arm64) (traianus/app.py:188, :256-257). Same arithmetic class as the artefact, but
  single-text and batched encoding are not guaranteed bit-identical: a measured figure on the
  artefact and the rendered map can differ at ≈ 1e-7. Closed by decision (POC.md, Corpus
  loading): the engine is loaded with the artefact's vectors, one at a time, in text order,
  through /ingesta/vector, which stores v̂ (Conversions above, computed as K6 does) byte for
  byte, not the received row widened (verified 2026-09-19, tests/integration/
  test_vector_ingest_bit_integrity.py).

Random numbers
  numpy.random.Generator(PCG64(20260918)), draws in the order each record fixes. Streams are
  reproducible only under the pinned numpy (2.4.1, pyproject.toml): NEP 19 does not guarantee
  Generator method streams across numpy versions.

Determinism
  Bit-reproducible only on the same numpy version, BLAS build, thread count and CPU. Every script
  sets OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1 before importing numpy
  and records np.show_config(), platform.platform() and the three digests in its result. Across
  environments, results agree within the derivations' tolerance rule, not bitwise; every decision
  records its margin to its threshold, so a flip caused by rounding is visible.

Results (outputs)
  data/refapp/<ID>_result.json: UTF-8, LF, json.dumps(sort_keys=True, indent=2, allow_nan=False);
  floats written by Python's repr (shortest round-trip), so every binary64 value is recovered
  exactly on read. The result's sha256 is written into the record before any consumer uses it.

Wire to the client (rendering, not measured)
  /spatial JSON numbers (binary64 repr, exact) → JavaScript Number (binary64, exact) → packed into
  the 64-byte node block: bytes 0–23 x, y, z, l, c, h as little-endian binary32; 24–55 node id as
  32 ASCII hex characters; 56–63 zero (frontend/src/binary.ts, traianus/geometry/zero_copy.py).
  The binary32 cast has relative error ≤ 2⁻²⁴ ≈ 6e-8: two notes whose distances to q differ by
  less than that may swap order on screen relative to a binary64 measurement. Declared limit.
```

En palabras: los datos de entrada se identifican por su huella SHA-256, y ningún script corre si no
coinciden. Después se eliminan los nulos: ningún NaN ni infinito, ninguna fila con longitud fuera
de 1 ± 3e-5, ninguna etiqueta vacía o repetida. Y se demuestra rompiéndolo: los tests cambian un
solo bit y exigen que se detecte. En el archivo lo detecta siempre la huella. En memoria (corregido el
2026-09-19), un bit alto del exponente multiplica la componente por una potencia enorme de 2 y la
validación lo detecta siempre; el bit bajo del exponente la duplica o la divide por dos, y solo se
detecta si la componente pasa de ≈ 0,0045 (al duplicarse) o ≈ 0,0089 (al dividirse): por debajo,
el cambio de longitud cabe en la tolerancia. Si la componente era cero o subnormal, ese bit la
convierte en un número normal diminuto (del orden de 2⁻¹²⁶), y pasa. Un bit de la mantisa cambia
la componente como mucho a la mitad (el bit más alto) y mucho menos los demás: solo se detecta en
los bits altos de componentes grandes (el bit 22, a partir de ≈ 0,0069); los bits 0 a 7 no se
detectan nunca. Un bit de signo no cambia la longitud, y el bit más bajo de la mantisa es
indistinguible del redondeo: ninguna validación los ve, solo la huella del archivo, y los tests lo
dejan escrito. La huella se calcula sobre los mismos bytes que se leen, en una sola lectura; las
etiquetas deben tener "part" no vacío y los ejes identificadores distintos (corregido el
2026-09-19). Pasar de float32 a float64 no cambia ningún bit del valor; renormalizar sí, y depende
del orden en que se suman los productos. Por eso los resultados solo son idénticos bit a bit en el
mismo entorno (versión de numpy, BLAS, hilos, CPU); entre máquinas coinciden dentro de una
tolerancia, y cada decisión guarda su margen al umbral para que un cambio por redondeo se vea. El
mapa que dibuja el motor sale de vectores codificados de uno en uno; las mediciones, del artefacto
codificado en lote: pueden diferir en torno a 1e-7, y está declarado. Al cargar el artefacto por
/ingesta/vector, el motor guarda byte a byte el mismo v̂ que mide K6, no la fila recibida
(verificado el 2026-09-19). En la pantalla las
coordenadas viajan como float32, con un error relativo de hasta 6e-8.

## 1. K6 — colour channel predictability

```
Input    V ∈ ℝ^{2221×384} (§0), rows unit; FIT = rows 0, 2, 4, …; EVAL = rows 1, 3, 5, … (1,110).
         A = (â_1 … â_8) ∈ ℝ^{8×384} (§0). Seed 20260918.
Output   data/refapp/K6_result.json with: digests; environment; ranking_fit, ranking_full
         (axis ids by rank); fallback flag per dipole; per step s (amended 2026-09-19): τ_s,
         tau_sigma_reference (the 989th smallest R² of the Σ-weighted null on B_s, reported
         only), cond(B_s), R²_s and adjusted R²_s of every candidate tested at step s; every
         remaining candidate logged with its outcome (selected, discarded, not_reached);
         selected channel or "none"; a step with no remaining candidate logged as not run;
         positive and calibration controls with their measured values and deviations; clip
         fractions; validity (amended 2026-09-19): valid (bool), first_failed_condition (null
         when valid), failed_conditions (every failed condition, in check order: dipole-1
         fallback; then per step cond(B_s) ≤ 1e5, the positive control (step 1), each control's
         exactness and its side). valid = false ⇒ no candidate result may be used.
         Identifiers, in that order (amended 2026-09-19): dipole_1_fallback; for each step s
         that ran: step_s_cond, positive_control (s = 1 only), step_s_control_in_exact,
         step_s_control_in_side, step_s_control_out_exact, step_s_control_out_side.
         Basis column names (amended 2026-09-19): 1, z(x), z(y), z(x)^2, z(y)^2, z(x)z(y),
         z(c_j:<name>) for the j-th selected channel.
Function
  ranking: order k by mean_{v ∈ FIT} ⟨v, â_k⟩, descending; ties by axis id.
  frame:   ĉ₁ = â_(1); dipole j ∈ {1, 2, 3} = (â_(2j), â_(2j+1)); w_j = P⊥â_(2j) − P⊥â_(2j+1).
  on EVAL: x = ⟨v, w_1⟩/‖w_1‖², y = ⟨v, ĉ₁⟩,
           λ₂ = ⟨v, w_2⟩/‖w_2‖², λ₃ = ⟨v, w_3⟩/‖w_3‖², a₈ = ⟨v, P⊥â_(8)⟩/‖P⊥â_(8)‖²,
           l = 1 / (1 + Var_k ⟨v, â_k⟩)  (population variance over the 8 axes).
  B_s = [1, x̃, ỹ, x̃², ỹ², x̃ỹ, c̃_1 … c̃_{s−1}] (amended 2026-09-19): x̃ = z(x), ỹ = z(y),
           c̃_j = z(c_j), z(u) = (u − ū)/sd(u) on EVAL, ddof = 0; products formed after z.
           span(B_s) = span of the raw columns, so R² is unchanged (D6); cond(B_s) is that of
           this matrix.
  R²(u; B) = 1 − ‖u − B β̂‖² / ‖u − ū‖², β̂ = argmin ‖u − Bβ‖ (numpy.linalg.lstsq);
           adjusted R² = 1 − (1 − R²)(n − 1)/(n − k), n = 1,110, k = columns of B incl. 1.
  τ_s = sort(R²(n_i; B_s), i = 1…1000)[988], n_i = ⟨v, w⁰_i⟩/‖w⁰_i‖², w⁰_i = P⊥g_i/‖P⊥g_i‖.
  Σ-weighted null (reference only, amended 2026-09-19): as n_i with g_i = X_cᵀz_i/√1110,
           X_c = EVAL centred on its column means, z_i ~ N(0, I_1110) drawn after the deciding
           null from the same generator; tau_sigma_reference_s = sort(R²; B_s)[988].
  selection: c_s = first remaining candidate with R²(·; B_s) ≤ τ_s; failures discarded.
```

En palabras: se ordenan los 8 ejes por lo mucho que el corpus (mitad FIT) se proyecta sobre cada
uno. El primero es el ancla, y los siguientes forman tres dipolos por parejas. Sobre la otra mitad
(EVAL) se calculan la posición (x, y) y cuatro candidatos a color. Para cada candidato se mide qué
parte de su variación explica un polinomio de segundo grado de la posición y de los colores ya
elegidos (R²). Se compara con lo que explicaría una dirección cualquiera, sorteada 1.000 veces: si
el candidato no se parece a la posición más que el valor 989 de esas 1.000, se acepta. Se eligen
así, en orden, hasta tres colores. Antes de ajustar, cada columna (x, y y los colores ya elegidos)
se centra y se divide por su desviación típica, y los cuadrados y productos se forman después: la
escala de una dimensión no dice nada de ella, y el R² no cambia (corregido el 2026-09-19). El
resultado guarda, en cada paso, qué candidatos se probaron (con su R² y su R² ajustado), cuál se
eligió, cuáles se descartaron y cuáles no llegaron a probarse. Si falla alguna condición de
validez, el resultado lo dice (valid = false, la primera condición fallida y la lista completa) y
ningún consumidor puede usarlo. Los nombres de esas condiciones, su orden y los nombres de las
columnas de la base quedan fijados en el contrato; el null ponderado por Σ, que solo se reporta y
nunca decide, también queda definido aquí (corregido el 2026-09-19).

## 2. R4 — neighbourhood kept in a 5D perspective

```
Input    V_EVAL ∈ ℝ^{1110×384} (§0, K6's EVAL); K6_result.json (sha256 in R4.md; R4 refuses
         to run on a K6_result.json with valid = false, amended 2026-09-19); A (§0);
         seed 20260918.
Output   data/refapp/R4_result.json with: digests; environment; per L in {1, 2, 5, 10, 20, 50}:
         D̄, interval [lo, hi], Monte Carlo neighbours of both bounds, decision; y-only control
         (15/15 count, ties, near-duplicates); permutation control mean; fallback count;
         reported-only figures (2D, 5D − 2D, k = 5 and 50, L_gt, Σ-weighted reference, per-channel
         R² on the perspective); overall decision and margin of every hi to 0.
Function
  G = V V^T (binary64).
  N_q = the 15 notes j ≠ q with largest G[q, j] (ties: lower index).
  perspective(q, h): coordinates of every j ≠ q = (⟨v_j, h⟩, G[q, j], colours_j) — h = w_q
           (operator: poles = the two â with largest ⟨q, â⟩) or u_i = P_q⊥e_i/‖P_q⊥e_i‖
           (random) or absent (y-only); each column z-scored over j ≠ q; q mapped alike.
  M_q(h) = the 15 notes j ≠ q nearest to q in that space (Euclidean; ties: lower index).
  recall(q, h) = |N_q ∩ M_q(h)|  ∈ {0, …, 15}.
  D_q = recall(q, w_q) − mean_i recall(q, u_i);  D̄ = mean_q D_q.
  interval: block bootstrap over q (block length L) and over i, 10,000 resamples;
           [sorted[249], sorted[9749]].
  decision: R4 holds ⇔ hi < 0 for every L.
```

En palabras: para cada nota q de la mitad EVAL se buscan sus 15 vecinas reales (las de mayor
similitud en 384 dimensiones). Luego se dibuja la perspectiva de q: en vertical la similitud con q,
en horizontal el contraste λ del operador, y los colores fijos de cada nota. Se cuentan cuántas de
las 15 vecinas reales siguen entre las 15 más cercanas en ese dibujo. Se repite con 200
direcciones horizontales al azar en lugar de λ. La diferencia media dice si λ dispersa a las
vecinas más que un eje cualquiera. Para no fiarse de una sola cifra, se remuestrea por bloques de
notas contiguas y de direcciones; R4 se sostiene solo si, para todas las longitudes de bloque, el
intervalo entero queda por debajo de cero. Si el resultado de K6 no es válido (valid = false), R4
no se ejecuta (corregido el 2026-09-19).
