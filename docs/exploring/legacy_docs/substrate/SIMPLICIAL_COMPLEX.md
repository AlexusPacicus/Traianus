# Simplicial Complex Substrate ($S_n$)

## 1. State Definition

Traianus executes as a discrete, deterministic state machine. Following ADR-023, the computational state at ordinal sequence step $n$ ($n \in \mathbb{N}$) is defined as a finite simplicial complex:

$$S_n = (V_n, E_n, K_n)$$

Where:

- $V_n \subset \mathbb{R}^d$ — Finite set of $L_2$-normalized coordinate vectors (vertices).
- $E_n \subseteq V_n \times V_n$ — Deterministic adjacency edges formed strictly where $d(\mathbf{v}_i, \mathbf{v}_j) \leq \epsilon$.
- $K_n$ — Higher-order simplicial faces formed by sets of mutually adjacent vertices.

The active spatial basis matrix $B_n \in \mathbb{R}^{d \times k}$ is maintained in parallel by the Spatial Control Plane to calculate read-only projections $O_n = P_\theta(S_n)$ without mutating $S_n$.

## 2. Vertices ($V_n$)

Vertices are $L_2$-normalized coordinate vectors emitted by external representation providers. Each vertex is persisted in `manifold_nodes` with a composite primary key `(id, seq)` and a monotonically increasing revision number `seq`. The current state of a vertex is the row with `MAX(seq)` for its `id`.

## 3. Edges ($E_n$) — $\epsilon$-Adjacency

Edges are deterministic and server-side. A pair $(v_i, v_j)$ forms an edge iff the $L_2$ distance between their vectors satisfies:

$$\|\mathbf{v}_i - \mathbf{v}_j\|_2 \leq \epsilon$$

The constant $\epsilon$ is server-side (`EPSILON_EDGE`). Edges are persisted as `auto-edge-*` rows in `manifold_edges` with append-only revision logging and `removed` tombstones for deleted edges. Manual `edge-*` rows are preserved.

Edge computation is triggered by `rebuild_epsilon_edges()` and persisted by `persist_epsilon_edges()`.

## 4. Simplicial Faces ($K_n$)

Faces are higher-order simplices formed by sets of mutually adjacent vertices. $K_n$ is deferred to WP2 (ADR-018/019) as the persistent homology and GUDHI C++ integration are not yet implemented. The PoC does not compute or store faces.

## 5. Invariants

- **Substrate Isolation:** The simplicial complex represents the computational state. It is neither the external phenomenon nor its observation.
- **Boundary Separation:** Representation providers generate coordinates; observation layers inspect state. Traianus governs the intermediate deterministic substrate.
- **Deterministic Construction:** Edges are computed deterministically from vector coordinates; no stochastic variation.

## 6. References

- ADR-023: Computational Spatial State Substrate
- ADR-018: Dynamic Dimension-k Discovery via Persistent Homology (deferred to WP2)
- ADR-019: Native Integration of GUDHI C++ Library (deferred to WP2)
- TRAIANUS_AUDIT.md: Finding H5 (E_n and K_n unimplemented)