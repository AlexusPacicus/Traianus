"""Polar Projector: stateless orthogonal decomposition over S^{d-1}."""

import numpy as np
from numpy.typing import NDArray


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
        """
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

        Args:
            c1_hat: Normalized anchor vector.

        Returns:
            Unit vector u⊥ orthogonal to ĉ₁.
        """
        # Find index of minimum absolute component (deterministic tie-breaking)
        k = int(np.argmin(np.abs(c1_hat)))

        # Canonical basis vector e_k
        e_k = np.zeros_like(c1_hat)
        e_k[k] = 1.0

        # Project out ĉ₁ component: e_k - ⟨e_k, ĉ₁⟩ĉ₁
        proj = np.dot(e_k, c1_hat)
        u_perp_raw = e_k - proj * c1_hat

        # Normalize
        norm = np.linalg.norm(u_perp_raw)
        if norm > 0:
            return u_perp_raw / norm

        # Unreachable defensive fallback: u_perp_raw == 0 requires e_k ∥ ĉ₁,
        # but k = argmin|ĉ₁| guarantees |ĉ₁[k]| <= 1/sqrt(d) < 1 for d >= 2,
        # so e_k - ⟨e_k,ĉ₁⟩ĉ₁ never vanishes. Kept to avoid div-by-zero.
        return e_k  # pragma: no cover

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

    def project(
        self,
        v_n: NDArray[np.float64],
        c_1: NDArray[np.float64],
        c_A: NDArray[np.float64],
        c_B: NDArray[np.float64],
        centroid_id: int,
    ) -> tuple[int, float, float]:
        """
        Execute full polar projection pipeline.

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
        # Ensure float64
        v_n = np.asarray(v_n, dtype=np.float64)
        c_1 = np.asarray(c_1, dtype=np.float64)
        c_A = np.asarray(c_A, dtype=np.float64)
        c_B = np.asarray(c_B, dtype=np.float64)

        # 1. Normalize anchor with null guard
        c1_hat = self._normalize_anchor(c_1)

        # 2. Orthogonal projection (associative O(d) form, no dense matrix)
        cA_perp = self._project_perp(c_A, c1_hat)
        cB_perp = self._project_perp(c_B, c1_hat)

        # 3. Compute dipole vector (with collinearity handling)
        v_dipole = self._compute_dipole(cA_perp, cB_perp, c1_hat)

        # 4. Projected residual
        r = self._project_perp(v_n - c_1, c1_hat)

        # 5. Affective voltage λ = ⟨r, v_dipole⟩ / ||v_dipole||²
        v_dipole_norm_sq = np.dot(v_dipole, v_dipole)
        if v_dipole_norm_sq > 0:
            lambda_val = float(np.dot(r, v_dipole) / v_dipole_norm_sq)
            # Clamp to [-1, 1] for numerical stability
            lambda_val = np.clip(lambda_val, -1.0, 1.0)
        else:
            # Unreachable: v_dipole is either cA_perp - cB_perp with norm >=
            # eps_collinear > 0, or 2*delta*u_perp with norm 2*delta > 0.
            lambda_val = 0.0  # pragma: no cover

        # 6. Escape distance d_esc = ||r - λ·v_dipole||
        d_esc = float(np.linalg.norm(r - lambda_val * v_dipole))

        return (centroid_id, lambda_val, d_esc)