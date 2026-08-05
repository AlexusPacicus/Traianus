# Transactional Persistence Substrate

## 1. Append-Only Revision Log

All persistent state entities (`manifold_nodes`, `manifold_edges`) use an append-only revision log with a composite primary key `(id, seq)`. Every state transition INSERTS a new revision row with a monotonically increasing `seq` value. No UPDATE, REPLACE, or DELETE operations modify existing rows.

Current state for any entity is retrieved as the row with `MAX(seq)` for its `id`.

## 2. Schema

```sql
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
);
```

| Field | Logical Type | Technical Purpose |
| :--- | :--- | :--- |
| `id` | Unique Identifier | Deterministic primary key (`NODE_{ingestion_id}`). |
| `seq` | Revision Sequence | Monotonically increasing revision number per `id`; current state = `MAX(seq)` per id. |
| `text` | Plain Text / Payload | Structured entity payload content (`RawDump` / `RefinedEntity`). |
| `toon_factor` | Single Character | Orthogonal Unicode symbol assigned via projection (`len == 1`). |
| `lifecycle_state` | State Enum | `'pending_approval'`, `'consolidated'`, `'incubating'`, `'telemetry_error'`, or `'archived'`. |
| `action_potential` | Continuous Scalar | Action potential for decay via Riemannian metric density (ADR-020). |
| `revision_milestone` | Boolean / Integer | Ethical Key validation marker for human-in-the-loop intervention (HITL). |
| `vector_blob` | Dense Binary Array | Dense float64 BLOB storage of normalized vector $v \in \mathbb{R}^d$. |
| `projections_json` | Multichannel Structure | Log of multi-axis projection spectrum onto active basis $B_n$. |
| `sys_internal_timestamp` | Substrate Index | Low-level transaction index and local delta synchronization marker. |

## 3. Migration Policy

Pre-existing rows (legacy schema with `id TEXT PRIMARY KEY`) are preserved as `seq=1` revisions during migration. No data is deleted. The legacy `INSERT OR REPLACE` and `UPDATE` patterns are replaced with `INSERT`-only operations.

## 4. Write-Ahead Logging (WAL)

Every database handler executes `PRAGMA journal_mode=WAL;` before any write operation. This ensures atomic commits and crash-safe persistence.

## 5. Edge History (Append-Only)

`manifold_edges` mirrors the same append-only pattern:
- Composite PK `(id, seq)`
- Each forged transition INSERTS a new revision with increasing `seq`
- `ON CONFLICT(id) DO UPDATE` upsert is PROHIBITED
- Stale `auto-edge-*` rows receive tombstone revision `state = 'removed'` (never deleted)
- Manual `edge-*` rows are preserved

## 6. Consolidation Semantics

Consolidation INSERTS a new revision (original not destroyed, H4). Missing node → `404`. The originally ingested content and its vector are preserved as earlier revisions.

## 7. References

- ADR-025: Non-Negotiable System State Invariants (Invariant #1: Monotonic Append-Only Evolution)
- ADR-026: Edge History Append-Only and the Geodesic Basis as Derived Artifact
- TRAIANUS_AUDIT.md: Findings H4, M7