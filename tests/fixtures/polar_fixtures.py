"""Shared fixtures for polar projector tests."""
import numpy as np
from numpy.typing import NDArray


def random_unit_vector(d: int, seed: int) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=d).astype(np.float64)
    return v / np.linalg.norm(v)


def random_centroids(d: int, k: int, seed: int) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    centroids = rng.normal(size=(k, d)).astype(np.float64)
    norms = np.linalg.norm(centroids, axis=1, keepdims=True)
    return centroids / norms


def collinear_centroids(anchor: NDArray[np.float64], d: int) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Generate c_A, c_B collinear with anchor (projected = 0)."""
    c_A = anchor * 1.5
    c_B = anchor * -0.7
    return c_A.astype(np.float64), c_B.astype(np.float64)


def simulate_drift_trajectory(steps: int, d: int, drift_rate: float, seed: int = 42) -> list[NDArray[np.float64]]:
    rng = np.random.default_rng(seed)
    trajectory = []
    v = random_unit_vector(d, seed)
    for i in range(steps):
        trajectory.append(v.copy())
        noise = rng.normal(scale=drift_rate, size=d).astype(np.float64)
        v = v + noise
        v = v / np.linalg.norm(v)
    return trajectory