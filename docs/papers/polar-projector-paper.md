# The Polar Projector: A Local O(d) Subspace Operator for Latent Tension Dissipation

**Author:**
**Affiliation:**
**Date:**

> Working mirror of the manuscript authored in Corca (https://corca.app/doc/er5CXGbjDUaGnbFE45Hse).
> Corca has no external read/write access from this repo and keeps no git-style history reachable
> from here, so this file is the version-controlled source of truth between sync passes — edit here,
> paste into Corca, or vice versa, and keep both in sync by hand.
>
> Status: DRAFT. Sections 1–3 are grounded (verified against `traianus/geometry/polar_projector.py`,
> `docs/LEDGER.md` seq 42, and `tools/experiments/verify_polar_delta_table.py`). Sections 4–7 are
> scaffolding only — see the TODO notes — and must not be treated as final until reviewed.
>
> Terminology: the title and body deliberately keep the native Traianus/Ulpia vocabulary
> ("Latent Tension Dissipation," "Collision Layer," tension/dissipation language) rather than a
> neutralized external-venue framing, so this paper stays consistent with the rest of the project's
> documentation. This is a considered choice, not an oversight — an external reviewer unfamiliar
> with the project vocabulary may push back on the physical-metaphor framing in the title; the
> Notation table (below) is the intended bridge to standard terminology on first encounter.

---

## Abstract

Embedding-based information architectures suffer from scalability problems caused by coupling
persistent corpus storage with hot-path interaction state. Existing systems rely either on
quadratic-cost spatial simulations (\( O(N^2) \)) or on non-linear stochastic projections (t-SNE,
UMAP) that introduce spatial drift under incremental updates. While global projections excel at
static corpus visualization, they are ill-suited for hot-path control, where local spatial
continuity and deterministic repeatability are required.

To address this, we present the **Polar Projector**: a local subspace operator that acts as a
deterministic \( O(d) \) *Collision Layer* for managing interaction state in volatile memory. The
operator evaluates an incoming vector (\( v_n \)) against an active local anchor, operating
completely isolated from persistent disk storage and independently of global corpus size
(\( N \)). We show that the projection is governed by a latent-energy conservation principle, and
that collinearity singularities in the tangent plane are mitigated by a deterministic canonical
fallback in the anchor's null space (a deterministic backward support perpendicular).

The benchmark suite measured projection latency at \( \approx 13.7\,\mu\text{s} \) with the
stateless entry point and \( \approx 6.3\,\mu\text{s} \) once the local frame is prepared once per
active context — flat across corpus sizes from 1,000 to 25,000 vectors, consistent with the
operator's proven independence from \( N \).

## 1. Introduction

Representing information via continuous vector embeddings rigidly couples two independent
operational dimensions:

1. **Interaction state:** volatile, short-lived trajectory dynamics in hot memory.
2. **Persistence state:** immutable, corpus-wide data structures stored on disk.

Reusing global visualization techniques (such as t-SNE or UMAP) to manage local interaction state
introduces two fundamental limitations. First, stochastic re-optimization alters existing
coordinates upon incremental updates, producing spatial drift that disrupts the user's spatial
mental model (Boechler, 2001). Second, global graph-layout algorithms scale quadratically
(\( O(N^2) \)), saturating the execution thread as corpus size grows.

The Polar Projector resolves these bottlenecks by formulating a distinct computational primitive: a
local, deterministic \( O(d) \) hot loop that operates exclusively on the active contextual
complement, deriving a projection coefficient (\( \lambda \in [-1.0, 1.0] \), the *Affective
Voltage*) and an orthogonal exploration residue (\( d_{esc} \), the *Escape Distance*) without
modifying or re-evaluating the global persistent corpus, with correctness guarantees proven in §2.

A third bottleneck — synchronous I/O blocking the interaction loop — is addressed at the systems
level within the Traianus substrate, where this operator's output feeds a signal-filtering stage
(a Schmitt Trigger) and an asynchronous batched-write path to SQLite WAL. That architecture is
**out of scope for this paper** and is treated in forthcoming work; the persistence-related numbers
reported in §3 are included only for deployment context, not as a claim proven here.

## Notation

This paper reuses domain-specific terms coined in the wider Traianus/Ulpia project. Each is a
proper technical object defined formally in §2; this table gives the standard-terminology
equivalent on first encounter, for readers unfamiliar with the project vocabulary.

| Term (this paper) | Symbol | Standard equivalent |
|---|---|---|
| Active Contextual Anchor | \( c_1 \) | reference/anchor centroid |
| Collision Layer / Polar Projector | \( P_\perp \) | rank-1 orthogonal projector, \( I - \hat{c}_1\hat{c}_1^T \), applied associatively |
| dipole vector | \( v_{dipole} \) | local basis direction (difference of projected secondary centroids) |
| Affective Voltage | \( \lambda \) | clipped least-squares projection coefficient of \( r \) onto \( v_{dipole} \) |
| Escape Distance | \( d_{esc} \) | orthogonal residual norm after regressing out \( v_{dipole} \) |

## 2. Main Result

*Proposition 1 (Complexity and Associative Equivalence).* Let \( v_n \in \mathbb{R}^d \) be an
incoming interaction vector, \( c_1 \in \mathbb{R}^d \) the Active Contextual Anchor, and
\( c_A, c_B \in \mathbb{R}^d \) secondary dipole centroids selected from a bounded active codebook
\( C \) ( \( |C| = K \leq 256 \) ). The anchor is normalized with a zero-guard threshold
\( \epsilon_{norm} > 0 \):

\[ \hat{c}_1 = \begin{cases} c_1 / \|c_1\|_2 & \text{if } \|c_1\|_2 > \epsilon_{norm} \\ 0 & \text{otherwise} \end{cases} \]

The orthogonal projector \( P_\perp: \mathbb{R}^d \to \mathbb{R}^{d-1} \) onto the complement of
\( \hat{c}_1 \) evaluates associatively as \( P_\perp v = v - \langle v, \hat{c}_1 \rangle \hat{c}_1 \),
in \( O(d) \) time and space without materializing the dense \( d \times d \) matrix
\( I - \hat{c}_1\hat{c}_1^T \). Codebook selection over \( K \leq 256 \) (a bounded constant, not
asymptotic in \( d \) or \( N \)) adds \( O(K \cdot d) \); the full evaluation is \( O(d) \),
independent of corpus size \( N \).

*Proposition 2 (Guaranteed Dipole Non-Degeneracy).* Assume \( \delta > 0 \),
\( \epsilon_{collinear} > 0 \) and \( d \geq 2 \). Let \( c_A^\perp = P_\perp c_A \),
\( c_B^\perp = P_\perp c_B \). The dipole vector

\[ v_{dipole} = \begin{cases} c_A^\perp - c_B^\perp & \text{if } \|c_A^\perp - c_B^\perp\|_2 \geq \epsilon_{collinear} \\ 2\delta \cdot u_\perp & \text{otherwise} \end{cases} \]

satisfies \( \|v_{dipole}\|_2 \geq \min(\epsilon_{collinear}, 2\delta) > 0 \) for every
configuration. In the degenerate case, \( k = \arg\min_i |\hat{c}_1[i]| \) satisfies
\( |\hat{c}_1[k]| \leq 1/\sqrt{d} \) (RMS bound on a unit vector), so
\( u_\perp = \text{normalize}(e_k - \langle e_k, \hat{c}_1 \rangle \hat{c}_1) \) is well-defined for
\( d \geq 2 \), since \( \|u_\perp^{raw}\|_2^2 \geq 1 - 1/d > 0 \).

*Remark.* Deterministically constructing a vector orthogonal to a single reference vector, without
an arbitrary sign or branch choice, is a well-studied problem in computer graphics for per-pixel
tangent-frame construction (Duff et al., 2017). That work optimizes a branchless, sign-based
construction for GPU evaluation at every shading point; the \( \arg\min \) + Gram-Schmidt
construction here instead targets a single CPU-resident fallback triggered only on the collinear
branch of Proposition 2, where per-call branch cost is irrelevant and analytical simplicity is the
only requirement.

The fallback vector also admits a closed scalar form, since \( e_k \) is one-hot:
\( \langle e_k, \hat{c}_1 \rangle = \hat{c}_1[k] \), and because \( \|\hat{c}_1\|_2 = 1 \),

\[ \|e_k - \hat{c}_1[k]\hat{c}_1\|_2 = \sqrt{1 - \hat{c}_1[k]^2} \]

— an exact identity, not an approximation (expand the square: the cross-term collapses using
\( \sum_{i\neq k}\hat{c}_1[i]^2 = 1-\hat{c}_1[k]^2 \)). This lets \( u_\perp \) be built directly as
\( u_\perp[k] = \sqrt{1-\hat{c}_1[k]^2} \), \( u_\perp[i] = \alpha\hat{c}_1[i] \) for \( i \neq k \),
with \( \alpha = -\hat{c}_1[k]/\sqrt{1-\hat{c}_1[k]^2} \), replacing the \( e_k \) allocation, dot
product, and vector-norm reduction with one scalar square root and a single scaled pass over
\( \hat{c}_1 \). This affects only the rare collinear-fallback branch inside `prepare()` — not the
per-stimulus `evaluate()` hot loop the §3 latency figures characterize — so its benefit is
implementation simplicity for that one branch, not a change to the paper's headline latency claims.

*Proposition 3 (Latent Energy Decomposition).* Let \( r = P_\perp(v_n - c_1) \),
\( \lambda^* = \langle r, v_{dipole} \rangle / \|v_{dipole}\|_2^2 \),
\( \lambda = \text{clip}(\lambda^*, -1, 1) \) (the *Affective Voltage*), and
\( d_{esc} = \|r - \lambda \cdot v_{dipole}\|_2 \) (the *Escape Distance*). Decomposing
\( r = \lambda v_{dipole} + (r - \lambda v_{dipole}) \):

\[ \|r\|_2^2 = \|\lambda v_{dipole}\|_2^2 + d_{esc}^2 + 2\lambda(\lambda^* - \lambda)\|v_{dipole}\|_2^2 \]

When \( |\lambda^*| \leq 1 \), \( \lambda = \lambda^* \) and the cross-term vanishes: exact
Pythagorean equality. When \( |\lambda^*| > 1 \) (saturation), the cross-term is strictly positive:
the clip dissipates latent energy rather than conserving it exactly. ∎

*Corollary (Energy Form).* The decomposition above is native to squared (energy) units. Writing
\( E_\lambda = \lambda^2 \|v_{dipole}\|_2^2 \) (channeled energy — computable from \( \lambda \) and
the frame's already-stored \( \|v_{dipole}\|_2^2 \), at no extra cost) and
\( E_{esc} = d_{esc}^2 \) (dissipated energy), the exact case reads
\( \|r\|_2^2 = E_\lambda + E_{esc} \): a direct sum of energies, matching this paper's *Latent
Tension Dissipation* framing more literally than the linear quantities \( \lambda, d_{esc} \) do.
This is an exposition device, not an implementation instruction: \( E_{esc} \) must still be
computed by squaring the numerically stable vector-form residual of §3.2
(\( \|r - \lambda v_{dipole}\|_2^2 \)), never via the algebraically expanded
\( \langle r,r\rangle - 2\lambda\langle r,v_{dipole}\rangle + \lambda^2\|v_{dipole}\|_2^2 \) — that
expansion is exactly the *scalar form* §3.2 measured losing all precision below
\( d_{esc}/\|r\|_2 \approx 10^{-6} \), which is precisely the near-collinear regime where an energy
reading would most need to be trustworthy.

## 3. Numerical Behavior

Benchmarked locally over \( N = 25{,}000 \) vectors ( \( d = 384 \), float64):

| Corpus Size (N) | Polar Projector Mean (µs) | Polar Projector p95 (µs) | \( O(N^2) \) Force Simulation |
|---|---|---|---|
| 1,000 | 13.65 | 14.20 | 0.955 s |
| 2,221 | 13.66 | 14.54 | 5.595 s |
| 4,000 | 13.68 | 14.12 | 19.800 s |
| 25,000 | 13.73 | 13.88 | 767.2 s (least-squares fit \( 1.228 \times 10^{-6} N^2 \), extrapolated) |

Projection latency stays flat as \( N \) grows — consistent with Proposition 1's independence from
corpus size — while the \( O(N^2) \) force baseline it replaces grows quadratically.

*Deployment context (not a claim of this paper — see §1 scope note):* within the Traianus
substrate, the persistence layer consuming this operator's output measured 25,000 embeddings
(76.8 MB) ingested in 1.38 s, async re-indexing in 66 ms, and 0 `SQLITE_BUSY` lock events across
191 concurrent readers (4.33–5.19 ms read latency). These numbers characterize the substrate the
benchmarks above were run in, not the operator itself.

### 3.1 Frame Preparation vs. Per-Stimulus Cost

The anchor normalization, dipole-pole projections and dipole construction of Proposition 1 depend
only on \( (c_1, c_A, c_B) \) — not on \( v_n \) — so they are invariant across every stimulus
evaluated under one active context. Splitting the operator into `prepare()` (frame construction)
and `evaluate()` (per-stimulus) separates the two costs:

| Stage | Mean (µs) | p95 (µs) |
|---|---|---|
| Full stateless call | 13.68 | 14.64 |
| `prepare()` — invariant frame | 6.87 | 7.18 |
| `evaluate()` — per stimulus | 6.34 | 6.68 |

Means over three runs of 25,000 stimuli each at \( d = 384 \), float64, fixed seeds
(`tools/experiments/decompose_polar_latency.py`); run-to-run spread is under 2%. Frame construction
accounts for 50.2% of a stateless call, so hoisting it out of the loop leaves **2.16× less work per
interaction** whenever the active context outlives a single stimulus. The stateless baseline here
(13.68 µs) is consistent with the 13.65–13.73 µs range measured independently in the table above.

### 3.2 Conditioning of the Escape Distance

Proposition 3's decomposition is an exact identity, and rearranging it expresses \( d_{esc} \)
purely in scalars already computed for \( \lambda \):
\( d_{esc}^2 = \langle r,r \rangle - 2\lambda\langle r, v_{dipole} \rangle + \lambda^2\|v_{dipole}\|_2^2 \),
which is 1.23× faster than evaluating \( \|r - \lambda v_{dipole}\|_2 \) directly. It is, however,
not a usable substitute: it subtracts nearly equal quantities as \( d_{esc} \) shrinks relative to
\( \|r\|_2 \). Against a construction whose exact escape distance is known analytically:

| \( d_{esc}/\|r\|_2 \) | Vector-form rel. error | Scalar-form rel. error |
|---|---|---|
| \( 10^{-3} \) | \( 1.2 \times 10^{-14} \) | \( 1.1 \times 10^{-10} \) |
| \( 10^{-5} \) | \( 1.1 \times 10^{-12} \) | \( 4.5 \times 10^{-7} \) |
| \( 10^{-7} \) | \( 9.8 \times 10^{-11} \) | \( 1.2 \times 10^{-3} \) |
| \( 10^{-8} \) | \( 6.7 \times 10^{-10} \) | \( 1.0 \times 10^{0} \) |

Below \( d_{esc}/\|r\|_2 \approx 10^{-6} \) the scalar form returns values uncorrelated with the
true distance, while the vector form degrades gracefully across the full sweep. The identity of
Proposition 3 therefore stands as a theorem but not as an algorithm: the residual is computed in
vector space before the norm is taken. This regime — a stimulus lying almost entirely along the
dipole axis — is precisely the one where \( \lambda \) saturates, so precision there is not
incidental.

### 3.3 δ-Sweep Behavior

Varying the fallback scale \( \delta \) (Proposition 2) under the controlled collinearity scenario
(\( d = 384 \), fixed seed) traces the sensitivity of \( \lambda \) and \( d_{esc} \) to the
canonical fallback:

| \( \delta \) | \( \sigma^2_\lambda \) | \( \sigma^2_{d_{esc}} \) | \( R = \sigma^2_\lambda / \sigma^2_{d_{esc}} \) |
|---|---|---|---|
| 0.001 | 9.782e-1 | 3.535e-6 | 276747.31 |
| 0.010 | 7.994e-1 | 3.886e-6 | 205690.72 |
| 0.050 | 2.401e-1 | 6.651e-6 | 36104.25 |
| 0.100 | 6.594e-2 | 6.954e-6 | 9482.78 |
| 0.200 | 1.649e-2 | 6.954e-6 | 2370.69 |
| 0.500 | 2.638e-3 | 6.954e-6 | 379.31 |

Generated by `tools/experiments/generate_polar_delta_table.py` at \( N = 10{,}000 \) samples per
row (2-sigma sampling bound ≈ 2.8% on the reported variances) — fully deterministic under the
fixed seed, so any reader can regenerate this exact table. \( \sigma^2_{d_{esc}} \) saturates at a
constant floor for \( \delta \geq 0.1 \), where the fallback branch stops dominating the residual;
below that, shrinking \( \delta \) inflates \( R \) by orders of magnitude as the dipole norm
collapses toward its \( 2\delta \) floor (Proposition 2).

*Methodological note:* an earlier pass of this table at \( N = 1{,}000 \) reproduced only 4 of 6
rows within a 5% tolerance band — the two small-\( \delta \) rows deviated by 9–12%, consistent
with the theoretical ≈4.5% sampling error at that N in the near-collinear regime. This table
supersedes it.

## 4. Extensions

> TODO — draft, not reviewed. Candidate directions, scoped strictly to the Polar Projector itself
> (not the broader Ulpia/Traianus system). None of the mechanisms below exist in
> `traianus/geometry/polar_projector.py` today — each is a proposed direction, not a description of
> current code.

### 4.1 Multi-Axis Tangent Frames and the Tripolar Model

The core Polar Projector derives a 1D scalar signal \( \lambda \) from a single projected dipole
\( v_{dipole} = P_\perp(c_A - c_B) \). This construction extends natively to \( m \)-dimensional
local tangent frames (\( m \ll d \)). Selecting additional secondary centroids
\( \{c_C, c_D, \dots\} \) and applying Gram-Schmidt orthogonalization within the null space of
\( \hat{c}_1 \) constructs an orthonormal basis \( \{u_1^\perp, u_2^\perp, \dots, u_m^\perp\} \).
Evaluating \( r \) across \( m \) orthogonal dipoles yields a multi-axis coordinate vector
\( \boldsymbol{\lambda} \in [-1.0, 1.0]^m \), resolving directional ambiguity in multi-faceted
local manifolds while preserving the \( \mathcal{O}(m \cdot d) \approx \mathcal{O}(d) \)
associative projection property (for \( m \) treated as a small bounded constant, not asymptotic
in \( d \) or \( N \) — same status as \( K \) in Proposition 1).

As a limiting 3-anchor case, a **Tripolar Model** would evaluate interactions against three key
anchors (\( c_1, c_{near}, c_{far} \)) instead of one. This could resolve directional ambiguity
across distant manifold regions without losing the \( \mathcal{O}(d) \) linear-time execution
guarantee. Nothing about this extension is concurrent or timing-related — it is a purely geometric
generalization of the single-anchor construction to multiple simultaneous anchors.

### 4.2 Batched Subspace Evaluation and Direct Energy Computation

The associative projection \( P^\perp v = v - \langle v, \hat{c}_1 \rangle \hat{c}_1 \) extends
directly to batched inputs \( V \in \mathbb{R}^{B \times d} \). Evaluating

\[ V P^\perp = V - (V \hat{c}_1) \hat{c}_1^T \]

the operator would process \( B \) candidate interaction vectors against a fixed frame
\( (c_1, c_A, c_B) \) in \( \mathcal{O}(B \cdot d) \) floating-point operations, without
instantiating a dense intermediate \( d \times d \) matrix — the same associative identity as
Proposition 1, applied row-wise.

In high-throughput hot loops, `evaluate()` could return the squared orthogonal residual energy
\( E_{esc} = \|r_{esc}\|_2^2 \) (§2, Corollary) instead of \( d_{esc} = \sqrt{E_{esc}} \), skipping
the square-root instruction. The practical benefit today is exactly that — one fewer instruction
per call — not gradient-safety: avoiding the singularity of \( \frac{d}{dx}\sqrt{x} \) at
\( x \to 0 \) only matters if a downstream consumer differentiates through \( E_{esc} \), and no
current Traianus consumer does (the substrate is a deterministic control plane, not a
gradient-based pipeline; see §1 scope note). As with the Corollary in §2, this must compute
\( E_{esc} \) by squaring the numerically stable vector-form residual, never the algebraically
expanded form §3.2 already showed loses precision near collinearity.

### 4.3 Adaptive Scale Calibration

In the core formulation, the fallback scale factor \( \delta \) is a static hyperparameter
(\( \delta = 0.100 \)). An adaptive calibration rule could instead scale \( v_{dipole} \)
dynamically relative to local manifold dispersion:

\[ \delta_{local} = \eta \cdot \frac{1}{|\mathcal{C}|} \sum_{i \in \mathcal{C}} \|c_i - c_1\|_2 \]

where \( \eta > 0 \) is a global scaling constant and \( \mathcal{C} \subset \mathcal{C}_{active} \)
is the active local neighborhood. Scaling the synthetic dipole diameter dynamically could prevent
artificial voltage saturation in dense subspaces. Proposition 2's non-degeneracy bound
\( \|v_{dipole}\|_2 \geq \min(\epsilon_{collinear}, 2\delta_{local}) > 0 \) would still hold under
this substitution, but only conditionally: it requires \( \delta_{local} > 0 \), i.e. \( \eta > 0 \)
and \( \mathcal{C} \) not entirely coincident with \( c_1 \) (every \( c_i = c_1 \) drives
\( \delta_{local} \to 0 \), degrading the bound along with it — see §6 for this edge case).

### 4.4 Active Codebook Capacity

Proposition 1 assumes secondary dipole centroids are selected from "a bounded active codebook
\( C \) (\( |C| = K \leq 256 \))" — this is a modeling assumption about an external caller, not
something implemented inside `traianus/geometry/polar_projector.py` today: no codebook data
structure, capacity bound, or eviction policy exists anywhere in the current codebase (`centroid_id`
is a bare, unbounded external identifier). Any discussion of behavior beyond \( K = 256 \) is
therefore conditional future work, not a description of an existing capacity story. *If* such a
codebook is implemented, keeping \( K \) small enough that centroid indices fit compact
representations and active-frame construction (\( \mathcal{O}(K \cdot d) \approx \mathcal{O}(d) \))
stays cache-resident would matter; an LRU eviction policy or a hierarchical Product Quantization
(PQ) index are two candidate mechanisms for bounding \( K \) as active contexts grow past that
point — but confirming whether a codebook needs to exist at all, and at what layer, comes first.

## 5. Discussion

> TODO — draft, not reviewed.

*Scope guard.* This section argues determinism as a property of the **operator itself** — canonical
`argmin` tie-breaking, fixed-threshold clipping, no iterative optimization or random seed anywhere
in `project()` (Props 1–3) — not as a claim about the rest of whatever system consumes it. Whatever
else Traianus/Ulpia does architecturally is out of scope here and belongs to later, separate papers.

The projector \( P_\perp \) itself is not new: it is the standard rank-1 orthogonal complement, and
its associative form \( P_\perp v = v - \langle v, \hat{c}_1\rangle\hat{c}_1 \) is the same identity
underlying classical Gram-Schmidt orthogonalization — it is what lets Proposition 1 avoid
materializing the dense \( d \times d \) matrix, not a new mathematical object. The honest question
is not whether \( P_\perp \) is novel, but what this paper does with it that a reader already
familiar with that identity would not expect.

The closest structural precedent is debiasing word embeddings (Bolukbasi et al., 2016), which
learns a bias subspace from paired difference vectors and projects it out of the remaining
embeddings with the same rank-1 orthogonal complement used here. The distinction is *where and
when* \( P_\perp \) is applied: Bolukbasi et al. use it as a static, global, one-time preprocessing
pass over the whole corpus, permanently altering stored embeddings; the Polar Projector applies the
identical primitive as a volatile, per-interaction \( O(d) \) operator against one active anchor,
never touching persisted embeddings. This contrast pre-empts the most direct version of "this is
just embedding debiasing."

The dipole construction fares similarly under scrutiny. Projecting embeddings onto an axis defined
by the difference of two centroids, \( c_A - c_B \), is an established visualization technique (Liu
et al., 2018; Bandyopadhyay et al., 2022), so a pair-of-centroids dipole is not itself a
contribution. What those methods do not do, and what this operator does by construction, is remove
the anchor's own component from both poles *before* forming the axis: by linearity of \( P_\perp \),
\( P_\perp c_A - P_\perp c_B = P_\perp(c_A - c_B) \), so the dipole is anchored to the local
complement, not to the raw embedding space those visualization tools project onto directly.

One naming collision is worth flagging explicitly rather than leaving for a reader to discover
independently: at least one existing system (`chronos-vector`,
github.com/manucouto1/chronos-vector) uses the name "Anchor Projection" for
`project_to_anchors(traj, anchors, metric='cosine')` — cosine distance from a trajectory to
*multiple* anchors, producing a multi-anchor coordinate summary. This is a different mechanism from
the single-anchor rank-1 decomposition used here; the shared vocabulary is coincidental, not
structural.

None of the above is where this paper's claim to a contribution rests. That claim is determinism
itself, as a property of the operator, not as a slogan. Any system that reaches for a stochastic
method — t-SNE, UMAP, randomly-initialized force layout — to answer this specific question (how
does an incoming vector relate to one active local state) inherits spatial drift: identical
underlying data can render at different apparent positions across runs or incremental updates, so
spatial proximity stops reliably encoding semantic proximity. The Polar Projector does not inherit
this, by construction (Props 1–3, and the canonical `argmin` tie-break of Proposition 2's fallback
in particular), independent of anything else about the system that adopts it. This matters beyond
raw correctness: HCI research on hypertext navigation shows users build a persistent spatial mental
model of the interface they interact with, and that instability in that layout measurably degrades
navigation and orientation (Boechler, 2001) — a stable, reproducible operator is valuable for the
signal it produces (\( \lambda, d_{esc} \)), independent of any claim about how a downstream system
renders or persists positions.

The structurally closest prior art to the *shape* of this computation, rather than to its purpose,
is random-hyperplane locality-sensitive hashing (Charikar, 2002): both reduce to an inner product
against a reference direction. The two solve different problems. LSH is stochastic by design and
targets approximate similarity search over an entire corpus; the Polar Projector is deterministic,
uses one semantically-chosen anchor rather than a random one, and answers a local tension/collision
question against an active state, not a retrieval question over the whole dataset. This is the most
likely reviewer objection, so it is stated here directly rather than left implicit.

*A reading in terms of known and unknown.* Proposition 3's energy split (§2, Corollary) admits a
plain epistemic gloss worth stating once, explicitly, rather than left implicit in the
tension/energy vocabulary: \( E_\lambda \) is the portion of an incoming stimulus's energy that the
active local frame already explains — it lies along an axis built from two previously-observed
centroids — while \( E_{esc} \) is the portion that frame cannot account for. This reading has a
boundary worth stating alongside it, not hiding: a centroid is, by the defining property of the
arithmetic mean, the point that minimizes total squared distance to the group it summarizes — in
that precise sense it *is* the most "known" point of a unimodal neighborhood. But the same
construction can mislead for a bimodal one, where the mean falls in the gap between two clusters
rather than inside either — the least representative point of both. That is not a hypothetical
concern; it is the exact configuration Proposition 2's collinearity fallback exists to handle, so
the known/unknown reading and the paper's own non-degeneracy guarantee describe the same failure
mode from two directions.

## 6. Open Questions

> TODO — draft, not reviewed. Kept as a list rather than prose: each item below is an independent
> open problem, not a connected argument, and forcing narrative transitions between unrelated
> questions would manufacture connections that aren't there.

- **Tightness of the \( \epsilon_{collinear} \) vs. \( \delta \) bound in Proposition 2.** The
  guarantee \( \|v_{dipole}\|_2 \geq \min(\epsilon_{collinear}, 2\delta) \) is a worst-case bound;
  whether it is ever loose enough in practice to matter — whether real collinear configurations
  approach it — hasn't been measured. The δ-sweep in §3.3 varies \( \delta \) but doesn't
  specifically probe the tightness of this particular inequality.
- **Behavior under adversarial or fast-drifting anchors.** Every proposition here treats
  \( (c_1, c_A, c_B) \) as fixed for the duration of one `prepare()`/`evaluate()` cycle. What
  happens to \( \lambda \) and \( d_{esc} \) continuity if \( c_1 \) itself changes between calls
  faster than the interaction loop consumes them — is there a meaningful notion of Lipschitz
  continuity in the anchor, or does an anchor change simply invalidate the frame outright (the
  current `PolarFrame` design's implicit assumption)?
- **Required sample size for variance-sensitive metrics near the collinear regime.** §3.3's
  methodological note already found that \( N = 1{,}000 \) undersamples by 9–12% in the two
  smallest-\( \delta \) rows while \( N = 10{,}000 \) does not; this was resolved empirically for
  that one table, but the general relationship between \( \delta \), dimension \( d \), and the
  sample size needed for a trustworthy variance estimate near collinearity hasn't been turned into
  a guideline a reader could apply to a different sweep.
- **Further stabilization of the §3.2 vector-form residual.** The vector form degrades gracefully
  rather than catastrophically, but "gracefully" is not "exactly" — whether re-orthogonalization or
  another correction could tighten the vector-form error further in the regime where \( P_\perp \)
  suffers cancellation for stimuli nearly parallel to the anchor has been measured (§3.2's table)
  but not addressed algorithmically.
- **§4.3's adaptive \( \delta_{local} \) under a degenerate neighborhood.** If the active
  neighborhood \( \mathcal{C} \) collapses to points coincident with \( c_1 \) (or \( \eta \to 0 \)),
  \( \delta_{local} \to 0 \) and Proposition 2's non-degeneracy bound degrades along with it. §4.3
  states \( \delta_{local} > 0 \) as a precondition; what's missing is an explicit lower bound on
  \( \delta_{local} \) itself, analogous to how \( \delta \) is required `> 0` at construction time
  for the static case.

## Acknowledgements

> TODO.

## References

> Status: found via the Browser tool (per the option below) and user-verified prior to inclusion.
> Each entry is cited at least once above; none is a claim of direct novelty over this work — see
> §5 for how each relates to (and differs from) the Polar Projector.

1. Bandyopadhyay, S., Xu, J., Pawar, N., & Touretzky, D. (2022). Interactive Visualizations of Word
   Embeddings for K-12 Students. *Proceedings of the AAAI Conference on Artificial Intelligence*,
   36(11), 12713–12720.
2. Boechler, P. M. (2001). How Spatial Is Hyperspace? Interacting with Hypertext Documents:
   Cognitive Processes and Concepts. *CyberPsychology & Behavior*, 4(1).
3. Bolukbasi, T., Chang, K.-W., Zou, J., Saligrama, V., & Kalai, A. T. (2016). Man is to Computer
   Programmer as Woman is to Homemaker? Debiasing Word Embeddings. *Advances in Neural Information
   Processing Systems 29 (NeurIPS 2016)*. arXiv:1607.06520.
4. Charikar, M. S. (2002). Similarity Estimation Techniques from Rounding Algorithms. *Proceedings
   of the 34th Annual ACM Symposium on Theory of Computing (STOC 2002)*.
5. Duff, T., Burgess, J., Christensen, P., Hery, C., Kensler, A., Liani, M., & Villemin, R. (2017).
   Building an Orthonormal Basis, Revisited. *Journal of Computer Graphics Techniques*, 6(1).
6. Liu, S., Bremer, P.-T., Thiagarajan, J. J., Srikumar, V., Wang, B., Livnat, Y., & Pascucci, V.
   (2018). Visual Exploration of Semantic Relationships in Neural Word Embeddings. *IEEE
   Transactions on Visualization and Computer Graphics*, 24(1), 553–562.
   DOI:10.1109/TVCG.2017.2745141.
7. `chronos-vector` (manucouto1). Temporal vector database; "Anchor Projection" tutorial and
   `project_to_anchors()` API. https://github.com/manucouto1/chronos-vector — software, cited in
   §5 for terminology disambiguation only, not as academic prior art.
