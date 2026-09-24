# Traceability

What the engine promises, stated in words, pinned to the code that does it and to the test that
fails if it stops doing it. One entry per claim, in a fixed format, so a script can check every
entry and CI turns red when one lies.

Language: the document is English; each "En palabras" line is in Spanish by the author's decision,
as in `docs/methodology/instrument-audit/contracts.md`.

## Format

Each entry is a `###` heading `<ID> — <title>` followed by these field lines:

- `En palabras`: the claim, exactly once.
- `Code`: `` `<path>:<line>` — «`<anchor>`» ``, one or more. The anchor is an exact quote that
  occurs once in the file; it is normative, and the line is where it starts.
- `Test`: `` `<path>::<name>` `` or `` `<path>::<Class>::<name>` ``, one or more. An entry without a
  test does not belong here: citations do not prove conformance, tests do.
- `Source`: the clause or finding the claim comes from, exactly once.

`tools/audit/check_doc_citations.py` verifies every entry; `--fix` rewrites a stale line number.
The `path:line` citations in other documents (e.g. REMEDIATION-01) are dated records, not checked.

## Consolidation

### C1-SELF-PROJECTION — the dynamic threshold excludes self-projection

- **En palabras:** el umbral crítico se calcula solo con las proyecciones de cada eje sobre los
  demás; la de un eje sobre sí mismo (siempre 1.0) inflaría la varianza base.
- **Code:** `traianus/geometry/observables.py:24` — «`for j, other in enumerate(vectors) if j != i`»
- **Code:** `traianus/app.py:244` — «`return calibrate_critical_threshold(vectors)`»
- **Test:** `tests/unit/test_substrate.py::test_c1_threshold_excludes_self_projection`
- **Test:** `tests/unit/test_substrate_invariants.py::TestDualKeyC1Gate::test_calibration_deterministic_and_excludes_self_projection`
- **Source:** AGENTS 3.4 · AUDIT C1, key invariant 1

### DUAL-KEY — consolidation needs both keys at once

- **En palabras:** un nodo se consolida si y solo si su varianza alcanza el umbral y la llave
  ética es verdadera; ninguna de las dos basta sola.
- **Code:** `traianus/governance/gate.py:21` — «`topological_passed = variance >= threshold`»
- **Code:** `traianus/governance/gate.py:22` — «`is_consolidated = topological_passed and ethical_key`»
- **Test:** `tests/unit/test_substrate.py::test_evaluate_gate_v01_dual_key_requires_both`
- **Test:** `tests/unit/test_substrate_invariants.py::TestDualKeyC1Gate::test_dual_key_truth_table_over_synthetic_spectra`
- **Source:** AGENTS 3.5 (which names `traianus/core.py`; the gate lives in `traianus/governance/gate.py` and `core.py` re-exports it) · AUDIT key invariant 4

### ETHICAL-KEY-STRICT — the ethical key is a JSON boolean, never coerced

- **En palabras:** `/consolidar` exige la llave ética como booleano JSON; si falta, o llega como
  `"true"`, `"yes"` o `1`, responde 422 y no escribe ninguna revisión.
- **Code:** `traianus/app.py:176` — «`ethical_key: StrictBool = Field(`»
- **Test:** `tests/integration/test_map_governance.py::TestTwoKeys::test_ethical_key_is_required`
- **Test:** `tests/integration/test_map_governance.py::TestTwoKeys::test_ethical_key_must_be_a_json_boolean`
- **Source:** AGENTS 3.5 · LEDGER R3 (`StrictBool`)

### VECTOR-PATH-NO-ETHICAL-KEY — ingestion never consolidates

- **En palabras:** `/ingesta/vector` evalúa la puerta con la llave ética en falso, así que un nodo
  recién ingerido queda en incubación aunque pase la llave topológica; solo `/consolidar` consolida.
- **Code:** `traianus/app.py:560` — «`list(projections.values()), ethical_key=False, threshold=dynamic_threshold`»
- **Test:** `tests/unit/test_substrate_invariants.py::TestDualKeyC1Gate::test_ingesta_vector_requires_ethical_key`
- **Test:** `tests/integration/test_map_governance.py::TestTwoKeys::test_no_other_route_consolidates`
- **Source:** AGENTS 3.5 · ADR-022

## Persistence

### APPEND-ONLY-NODES — node history is an append-only revision log

- **En palabras:** cada cambio de un nodo añade una revisión nueva con `seq` creciente; las
  anteriores no se reescriben.
- **Code:** `traianus/storage/_storage.py:98` — «`PRIMARY KEY (id, seq),`»
- **Test:** `tests/unit/test_substrate.py::test_append_only_revision_log`
- **Test:** `tests/unit/test_substrate_invariants.py::TestWALAppendOnly::test_operational_replay_is_append_only`
- **Source:** AGENTS 4.1 · AUDIT H4, key invariant 2

### LIFECYCLE-STATES — four lifecycle states, no `archived`

- **En palabras:** la base de datos solo admite cuatro estados de ciclo de vida
  (`pending_approval`, `incubating`, `consolidated`, `telemetry_error`) y rechaza `archived`.
- **Code:** `traianus/storage/_storage.py:99` — «`CHECK (lifecycle_state IN ('pending_approval', 'incubating', 'consolidated', 'telemetry_error'))`»
- **Test:** `tests/unit/test_substrate.py::test_lifecycle_check_accepts_valid_states`
- **Test:** `tests/unit/test_substrate.py::test_lifecycle_check_rejects_archived_state`
- **Source:** AGENTS 4.2 · AUDIT key invariant 3

### EPOCH-PROVENANCE — the active seed is tagged `PROSTHETIC_NSM_V1`

- **En palabras:** los ejes de la base y los nodos quedan etiquetados con la época
  `PROSTHETIC_NSM_V1`. El valor por defecto de la DDL es la misma línea literal en
  `manifold_nodes` y en `geodesic_axes`, así que no se puede anclar de forma única; lo fijan los
  tests.
- **Code:** `traianus/geometry/spatial_observables.py:30` — «`EPOCH_PROVENANCE = "PROSTHETIC_NSM_V1"`»
- **Test:** `tests/unit/test_substrate.py::test_axes_anchored_to_prosthetic_epoch`
- **Test:** `tests/unit/test_substrate.py::test_nodes_anchored_to_base_epoch`
- **Source:** AGENTS 3.3 · AUDIT key invariant 5

### ACTION-POTENTIAL-UNSCALED — action potential is the measured variance

- **En palabras:** el potencial de acción guardado es la varianza medida, sin escalar, en la
  ingesta vectorial y en la consolidación.
- **Code:** `traianus/app.py:563` — «`action_potential = float(gate["topological_key"]["variance"])`»
- **Code:** `traianus/app.py:707` — «`action_pot = float(gate["topological_key"]["variance"])`»
- **Test:** `tests/unit/test_audit_resolved_claims.py::test_action_potential_is_variance_not_scaled`
- **Test:** `tests/unit/test_substrate_invariants.py::test_consolidar_action_potential_is_true_variance`
- **Source:** AUDIT M6 · ADR-005

## Ingress perimeter

### INGRESS-ALLOWLIST — `/ingesta` accepts `text/plain` only

- **En palabras:** `/ingesta` acepta solo `Content-Type: text/plain`; cualquier otro tipo recibe
  415.
- **Code:** `traianus/app.py:131` — «`ALLOWED_INGRESS_TYPES = {"text/plain"}`»
- **Code:** `traianus/app.py:419` — «`if content_type not in ALLOWED_INGRESS_TYPES:`»
- **Test:** `tests/security/test_security.py::test_zero_trust_ingress_allowlist`
- **Source:** AGENTS 2.3 · AUDIT H2

### INGRESS-NULL-BYTE — a null byte is rejected at the byte level

- **En palabras:** si el cuerpo de `/ingesta` contiene un byte nulo, en cualquier posición,
  responde 400 antes de decodificar.
- **Code:** `traianus/app.py:423` — «`if b"\x00" in raw_bytes:`»
- **Test:** `tests/security/test_security.py::test_ingesta_rejects_null_bytes`
- **Test:** `tests/security/test_security.py::test_ingesta_rejects_null_byte_at_end`
- **Source:** AGENTS 2.4

### INGRESS-STRICT-UTF8 — the body decodes as strict UTF-8

- **En palabras:** el cuerpo de `/ingesta` se decodifica como UTF-8 estricto; una secuencia
  inválida o sobrelarga responde 400.
- **Code:** `traianus/app.py:426` — «`text = raw_bytes.decode("utf-8", errors="strict")`»
- **Test:** `tests/security/test_security.py::test_ingesta_rejects_invalid_utf8`
- **Test:** `tests/security/test_security.py::test_ingesta_rejects_overlong_utf8`
- **Source:** AGENTS 2.4

### INGESTA-IDEMPOTENCY — `/ingesta` enforces its idempotency key

- **En palabras:** `/ingesta` exige `X-Idempotency-Key` no vacía; una clave repetida devuelve el
  mismo id de ingesta y no encola nada nuevo.
- **Code:** `traianus/app.py:432` — «`ingestion_id, duplicate = storage.enqueue_ingest(text, x_idempotency_key)`»
- **Code:** `traianus/storage/_storage.py:485` — «`"VALUES (?, ?) ON CONFLICT(idempotency_key) DO NOTHING",`»
- **Test:** `tests/security/test_ingesta_idempotency.py::test_ingesta_rejects_missing_idempotency_key`
- **Test:** `tests/security/test_ingesta_idempotency.py::test_ingesta_rejects_empty_idempotency_key`
- **Test:** `tests/security/test_ingesta_idempotency.py::test_ingesta_rejects_whitespace_idempotency_key`
- **Test:** `tests/unit/test_storage_hardening.py::test_enqueue_ingest_duplicate_returns_existing_id`
- **Source:** AGENTS 2.3 · LEDGER seq 57

### CORS-ENUMERATED — CORS origins are enumerated, never a wildcard

- **En palabras:** las credenciales CORS solo se permiten a los orígenes enumerados; no hay
  comodín.
- **Code:** `traianus/app.py:85` — «`ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]`»
- **Test:** `tests/unit/test_audit_resolved_claims.py::test_cors_origins_are_enumerated_no_wildcard`
- **Source:** AGENTS 2.2 · AUDIT H3

## Observation

### EPSILON-EDGES — ε-adjacency is computed with ε = 0.8 on read

- **En palabras:** la adyacencia local usa ε = 0.8 por defecto (distancia L2); `/relations` la
  calcula al leer y `/consolidar` no persiste aristas automáticas.
- **Code:** `traianus/config.py:8` — «`DEFAULT_EPSILON_EDGE = 0.8`»
- **Code:** `traianus/app.py:785` — «`for e in storage.rebuild_epsilon_edges(EPSILON_EDGE)`»
- **Test:** `tests/unit/test_substrate.py::test_epsilon_edges_adjacency`
- **Test:** `tests/unit/test_substrate.py::test_relations_computes_auto_edges_on_read`
- **Test:** `tests/unit/test_substrate.py::test_consolidar_does_not_persist_auto_edges`
- **Source:** AGENTS 4.3 · AUDIT H5

## Declared gaps

Claims in AGENTS or AUDIT that no test pins today, so they have no entry here:

- AGENTS 2.2: endpoints bind to `127.0.0.1`. Nothing in `traianus/` sets the bind host; it is
  whatever the process that launches uvicorn passes.
- AGENTS 4.1: no `UPDATE` or `DELETE` on `geodesic_axes` or node history. The tests pin the
  behaviour of `manifold_nodes` (APPEND-ONLY-NODES); the static check is
  `tools/audit/traianus_invariant_verifier.py` (TR-H4-001), which is a script, not a test.
- AGENTS 4.3: ε-adjacency never changes a lifecycle state. No test asserts it directly.
- AUDIT M6: the background text-ingestion path writes `action_potential = float(variance)` with no
  direct assertion (AUDIT already declares this).
