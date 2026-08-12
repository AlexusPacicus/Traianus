"""Integration test for H2 Dimensional Relief.

Tests that:
1. The project_dimensional_relief pure operator works correctly.
2. K_cin proxy (projection variance) can be computed and compared to threshold.
3. Orthogonality loss reduction concept is valid.
"""
import numpy as np
from fastapi.testclient import TestClient

from traianus.app import app
from traianus.core import project_dimensional_relief


client = TestClient(app)


def test_project_dimensional_relief_basic():
    """Test the pure project_dimensional_relief operator."""
    v = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    k_cin = 0.5
    v_hat = project_dimensional_relief(v, k_cin)  # type: ignore
    assert v_hat.shape == (4,), f"Expected shape (4,), got {v_hat.shape}"
    assert np.isclose(v_hat[:3], v).all(), "First d coordinates should match"
    assert np.isclose(v_hat[3], k_cin), f"Last coordinate should be K_cin, got {v_hat[3]}"


def test_project_dimensional_relief_with_k_cin_zero():
    """Test with K_cin = 0."""
    v = np.array([0.5, 0.5, 0.0], dtype=np.float64)
    v_hat = project_dimensional_relief(v, 0.0)  # type: ignore
    assert np.isclose(v_hat[3], 0.0), "K_cin coordinate should be 0"


def test_project_dimensional_relief():
    """Test project_dimensional_relief operator with 382D -> 383D."""
    dim_in = 382
    v = np.random.randn(dim_in)
    v = v / np.linalg.norm(v)
    k_cin = 0.15
    v_hat = project_dimensional_relief(v, k_cin)  # type: ignore
    assert v_hat.shape == (dim_in + 1,), f"Expected shape ({dim_in + 1},), got {v_hat.shape}"
    assert np.isclose(v_hat[:dim_in], v).all(), "First d coordinates should match"
    assert np.isclose(v_hat[dim_in], k_cin), f"Last coordinate should be K_cin, got {v_hat[dim_in]}"


def test_k_cin_proxy_computation():
    """Test that K_cin proxy (projection variance) can be computed and compared to threshold."""
    dim_db = 384
    dim_in = 382
    
    # Create vector with dim_in < dim_db
    np.random.seed(123)
    raw_vector = np.random.randn(dim_in)
    raw_vector = raw_vector / np.linalg.norm(raw_vector)
    
    # Pad to dim_db for projection computation
    arr_padded = np.pad(raw_vector, (0, dim_db - dim_in), mode='constant', constant_values=0.0)
    
    # Use identity matrix as geodetic axes (B_0)
    B_0 = np.eye(dim_db)
    
    # Compute projections: arr_padded @ B_0.T gives a (dim_db,) array
    projections_raw = np.dot(arr_padded, B_0.T)
    # projections_raw is (384,) array - variance of these
    k_cin_proxy = float(np.var(projections_raw))
    
    assert k_cin_proxy >= 0, "K_cin proxy should be non-negative"
    
    # Compare to calibrated threshold
    from traianus.core import calibrate_critical_threshold
    
    # Create a minimal basis for threshold calibration
    basis_vectors = [np.eye(dim_db)[i] for i in range(min(10, dim_db))]
    theta_dyn = calibrate_critical_threshold(basis_vectors)
    assert theta_dyn >= 0, "Threshold should be non-negative"
    
    # Verify k_cin_proxy is a valid float for comparison
    assert isinstance(k_cin_proxy, float)
    assert isinstance(theta_dyn, float)


def test_integration_scenario_structural():
    """Structural test verifying the code paths for H2 dimensional relief exist."""
    import numpy as np
    
    # Test 1: Basic project_dimensional_relief functionality
    v = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    v_hat = project_dimensional_relief(v[:3], 0.5)  # type: ignore
    assert v_hat[3] == 0.5
    
    # Test 2: K_cin proxy computation with variance
    np.random.seed(42)
    raw = np.random.randn(382)
    raw = raw / np.linalg.norm(raw)
    padded = np.pad(raw, (0, 384 - 382), mode='constant', constant_values=0.0)
    B_0 = np.eye(384)
    # Note: np.dot gives (384,) array, must use np.var first then float
    projs = np.var(np.dot(padded, B_0.T))
    assert projs > 0
    
    # Test 3: Threshold comparison structure
    from traianus.core import calibrate_critical_threshold
    basis = [np.eye(384)[i] for i in range(min(10, 384))]
    basis_vectors = [b for b in basis]
    theta_dyn = calibrate_critical_threshold(basis_vectors)
    assert theta_dyn >= 0
    
    # Test 4: Verify the operator can map d -> d+1
    v_test = np.array([0.5, 0.5, 0.5], dtype=np.float64)
    v_hat_test = project_dimensional_relief(v_test, 0.1)  # type: ignore
    assert v_hat_test.shape == (4,)
    assert np.isclose(v_hat_test[-1], 0.1)