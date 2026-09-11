"""Polar Projector: stateless orthogonal decomposition over S^{d-1}."""

from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray


class PolarFrame(NamedTuple):
    """Local frame induced by an anchor and a dipole pair.

    Depends only on (c₁, cₐ, c_b), so it is invariant across every stimulus
    evaluated under the same active context. See PolarProjector.prepare.
    """

    c_1: NDArray[np.float64]
    c1_hat: NDArray[np.float64]
    v_dipole: NDArray[np.float64]
    v_dipole_norm_sq: float


class PolarProjector:
    """
    Stateless projector for dynamic orthogonal decomposition.

    All computations in float64. Deterministic execution for fixed inputs in
    a fixed floating-point environment.

    Mathematical formulation:
    - Anchor normalization: ĉ₁ = c₁/||c₁|| if ||c₁|| > eps_norm else 0
    - Orthogonal projector: P⊥ = I - ĉ₁ĉ₁ᵀ, evaluated, without materializing
      the dense (d, d) matrix, as the associative O(d) form P⊥v = v - ⟨v, ĉ₁⟩ĉ₁
    - Dipole projection: cₐ⊥ = P⊥cₐ, c_b⊥ = P⊥c_b
    - Collinearity check: ||cₐ⊥ - c_b⊥|| < eps_collinear
    - Canonical u⊥: k = argmin|ĉ₁[i]|, u⊥ = normalize(e_k - ⟨e_k, ĉ₁⟩ĉ₁)
    - Dipole vector: v_dipole = cₐ⊥ - c_b⊥ (non-collinear) or 2δ·u⊥ (collinear)
    - Residual: r = P⊥(vₙ - c₁)
    - Affective voltage: λ = ⟨r, v_dipole⟩ / ||v_dipole||², clamped to [-1, 1]
    - Escape distance: d_esc = ||r - λ·v_dipole||
    """

    def __init__(
        self,
        delta: float = 0.1,
        eps_norm: float = 1e-9,
        eps_collinear: float = 1e-6,
    ) -> None:
        """
        Initialize PolarProjector with numerical guards.

        Args:
            delta: Scaling factor for fallback dipole when centroids are collinear.
            eps_norm: Threshold below which anchor norm is treated as zero.
            eps_collinear: Threshold for collinearity detection.

        Raises:
            ValueError: If any guard is non-positive. Each one carries a lower bound the
                geometry depends on: the fallback dipole has norm 2·delta, so delta <= 0
                collapses it; a non-positive eps_norm disables the null-anchor guard; a
                non-positive eps_collinear disables collinearity detection entirely.
        """
        if delta <= 0.0:
            raise ValueError(f"delta must be > 0 (fallback dipole norm is 2*delta), got {delta}")
        if eps_norm <= 0.0:
            raise ValueError(f"eps_norm must be > 0, got {eps_norm}")
        if eps_collinear <= 0.0:
            raise ValueError(f"eps_collinear must be > 0, got {eps_collinear}")

        self.delta = delta
        self.eps_norm = eps_norm
        self.eps_collinear = eps_collinear

    def _normalize_anchor(self, c_1: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Normalize anchor with null guard.

        Args:
            c_1: Anchor centroid vector.

        Returns:
            Normalized anchor ĉ₁ if ||c₁|| > eps_norm, else zero vector.
        """
        c1_norm = np.linalg.norm(c_1)
        if c1_norm > self.eps_norm:
            return c_1 / c1_norm
        return np.zeros_like(c_1)

    def _project_perp(
        self,
        v: NDArray[np.float64],
        c1_hat: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """
        Apply the orthogonal projector P⊥ = I - ĉ₁ĉ₁ᵀ associatively in O(d):
        P⊥v = v - ⟨v, ĉ₁⟩ĉ₁. No dense (d, d) matrix is materialized.

        Args:
            v: Vector to project (d,).
            c1_hat: Normalized anchor; the zero vector degrades to identity.

        Returns:
            Projected vector orthogonal to ĉ₁.
        """
        return v - np.dot(v, c1_hat) * c1_hat

    def _is_collinear(self, cA_perp: NDArray[np.float64], cB_perp: NDArray[np.float64]) -> bool:
        """
        Check if projected centroids are collinear.

        Args:
            cA_perp: Projected centroid A.
            cB_perp: Projected centroid B.

        Returns:
            True if ||cA_perp - cB_perp|| < eps_collinear.
        """
        return bool(np.linalg.norm(cA_perp - cB_perp) < self.eps_collinear)

    def _canonical_u_perp(self, c1_hat: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Deterministic Gram-Schmidt: u⊥ = normalize(e_k - ⟨e_k, ĉ₁⟩ĉ₁)
        where k = argmin |ĉ₁[i]|.

        This is fully analytical, no iterative loops or ambiguous sign choices,
        guaranteeing deterministic execution for fixed inputs in a
        floating-point environment.

        Closed form: since e_k is one-hot, ⟨e_k, ĉ₁⟩ = ĉ₁[k], and because ‖ĉ₁‖₂ = 1,
        ‖e_k - ĉ₁[k]·ĉ₁‖₂ reduces algebraically to sqrt(1 - ĉ₁[k]²) (see the Remark
        after Proposition 2 in docs/papers/polar-projector-paper.md §2). This builds
        u⊥ directly by scaling ĉ₁ and overwriting index k, with no e_k allocation,
        no dot product, and no vector-norm reduction — same result, fewer passes.

        Args:
            c1_hat: Normalized anchor vector.

        Returns:
            Unit vector u⊥ orthogonal to ĉ₁.
        """
        # Find index of minimum absolute component (deterministic tie-breaking)
        k = int(np.argmin(np.abs(c1_hat)))

        # s = ĉ₁[k]; the sqrt below is non-vanishing because k = argmin|ĉ₁| gives
        # |s| <= 1/sqrt(d) < 1, guaranteed by the d >= 2 precondition prepare() enforces.
        s = c1_hat[k]
        raw_norm = np.sqrt(1.0 - s * s)

        u_perp = (-s / raw_norm) * c1_hat
        u_perp[k] = raw_norm
        return u_perp

    def _compute_dipole(
        self,
        cA_perp: NDArray[np.float64],
        cB_perp: NDArray[np.float64],
        c1_hat: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """
        Compute dipole vector v_dipole.

        Non-collinear: v_dipole = cA_perp - cB_perp
        Collinear: v_dipole = 2δ·u⊥

        Args:
            cA_perp: Projected centroid A.
            cB_perp: Projected centroid B.
            c1_hat: Normalized anchor.

        Returns:
            Dipole vector.
        """
        dipole_diff = cA_perp - cB_perp
        if self._is_collinear(cA_perp, cB_perp):
            u_perp = self._canonical_u_perp(c1_hat)
            return 2.0 * self.delta * u_perp
        return dipole_diff

    def prepare(
        self,
        c_1: NDArray[np.float64],
        c_A: NDArray[np.float64],
        c_B: NDArray[np.float64],
    ) -> PolarFrame:
        """
        Build the local frame shared by every stimulus under the same anchor.

        Anchor normalization, dipole-pole projection and dipole construction depend
        only on (c_1, c_A, c_B). A caller holding an active context fixed across many
        stimuli builds the frame once here and passes it to evaluate(), instead of
        rebuilding it on every call as project() does.

        Args:
            c_1: Static anchor centroid (d,).
            c_A: Dipole pole A (d,).
            c_B: Dipole pole B (d,).

        Returns:
            Immutable PolarFrame carrying ĉ₁, v_dipole and ||v_dipole||².

        Raises:
            ValueError: If the inputs are not 1-D vectors of one common dimension d >= 2
                (d >= 2 is what makes the orthogonal complement of the anchor non-empty,
                and mismatched ranks would otherwise broadcast into a (d, d) matrix), or
                if the resulting dipole is degenerate.
        """
        c_1 = np.asarray(c_1, dtype=np.float64)
        c_A = np.asarray(c_A, dtype=np.float64)
        c_B = np.asarray(c_B, dtype=np.float64)

        if c_1.ndim != 1 or c_A.ndim != 1 or c_B.ndim != 1:
            raise ValueError(
                "anchor and dipole poles must be 1-D vectors; got shapes "
                f"c_1{c_1.shape}, c_A{c_A.shape}, c_B{c_B.shape}"
            )
        if c_A.shape != c_1.shape or c_B.shape != c_1.shape:
            raise ValueError(
                "anchor and dipole poles must share shape; got "
                f"c_1{c_1.shape}, c_A{c_A.shape}, c_B{c_B.shape}"
            )
        if c_1.shape[0] < 2:
            raise ValueError(f"d >= 2 required for a non-empty orthogonal complement, got d={c_1.shape[0]}")

        c1_hat = self._normalize_anchor(c_1)
        cA_perp = self._project_perp(c_A, c1_hat)
        cB_perp = self._project_perp(c_B, c1_hat)
        v_dipole = self._compute_dipole(cA_perp, cB_perp, c1_hat)

        v_dipole_norm_sq = float(np.dot(v_dipole, v_dipole))
        if v_dipole_norm_sq <= 0.0:
            raise ValueError(
                "degenerate dipole: ||v_dipole||^2 underflowed to zero in float64 "
                f"(delta={self.delta}, eps_collinear={self.eps_collinear})"
            )

        return PolarFrame(c_1, c1_hat, v_dipole, v_dipole_norm_sq)

    def evaluate(
        self,
        v_n: NDArray[np.float64],
        frame: PolarFrame,
        centroid_id: int,
    ) -> tuple[int, float, float]:
        """
        Evaluate one stimulus against a prepared frame.

        Args:
            v_n: Input stimulus vector (d,).
            frame: Frame returned by prepare().
            centroid_id: External codebook centroid identifier.

        Returns:
            Tuple (centroid_id, lambda_val, d_esc) where:
            - lambda_val ∈ [-1.0, 1.0] (affective voltage)
            - d_esc ≥ 0 (escape distance)

        Raises:
            ValueError: If v_n does not match the frame's dimension.
        """
        v_n = np.asarray(v_n, dtype=np.float64)

        if v_n.shape != frame.c_1.shape:
            raise ValueError(
                f"v_n shape {v_n.shape} does not match frame dimension {frame.c_1.shape}"
            )

        # Projected residual
        r = self._project_perp(v_n - frame.c_1, frame.c1_hat)

        # Affective voltage λ = ⟨r, v_dipole⟩ / ||v_dipole||², clamped.
        # prepare() rejects a degenerate frame, so the denominator is positive here.
        lambda_val = float(
            np.clip(np.dot(r, frame.v_dipole) / frame.v_dipole_norm_sq, -1.0, 1.0)
        )

        # Escape distance d_esc = ||r - λ·v_dipole||, kept in vector space: the
        # algebraically equivalent scalar form loses all precision once
        # d_esc/||r|| falls below ~1e-6 (tools/experiments/decompose_polar_latency.py).
        d_esc = float(np.linalg.norm(r - lambda_val * frame.v_dipole))

        return (centroid_id, lambda_val, d_esc)

    def project(
        self,
        v_n: NDArray[np.float64],
        c_1: NDArray[np.float64],
        c_A: NDArray[np.float64],
        c_B: NDArray[np.float64],
        centroid_id: int,
    ) -> tuple[int, float, float]:
        """
        Execute full polar projection pipeline for a single stimulus.

        Equivalent to prepare() followed by evaluate(); prefer that pair when the
        anchor and dipole poles are fixed across a run of stimuli.

        Args:
            v_n: Input stimulus vector (d,).
            c_1: Static anchor centroid (d,).
            c_A: Dipole pole A (d,).
            c_B: Dipole pole B (d,).
            centroid_id: External codebook centroid identifier.

        Returns:
            Tuple (centroid_id, lambda_val, d_esc) where:
            - lambda_val ∈ [-1.0, 1.0] (affective voltage)
            - d_esc ≥ 0 (escape distance)
        """
        return self.evaluate(v_n, self.prepare(c_1, c_A, c_B), centroid_id)