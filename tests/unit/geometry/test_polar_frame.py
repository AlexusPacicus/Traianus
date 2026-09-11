"""Unit tests for the prepare()/evaluate() split - frame reuse must not alter results."""
import numpy as np
import pytest

from traianus.geometry.polar_projector import PolarFrame, PolarProjector

DIMS = (128, 384, 768)
SEEDS = range(10)


def _inputs(d: int, seed: int):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(4):
        v = rng.normal(size=d).astype(np.float64)
        out.append(v / np.linalg.norm(v))
    return out


class TestPolarFrame:
    def setup_method(self):
        self.projector = PolarProjector()

    @pytest.mark.parametrize("d", DIMS)
    @pytest.mark.parametrize("seed", SEEDS)
    def test_prepare_evaluate_matches_project_bitwise(self, d, seed):
        v_n, c_1, c_A, c_B = _inputs(d, seed)

        direct = self.projector.project(v_n, c_1, c_A, c_B, 7)
        frame = self.projector.prepare(c_1, c_A, c_B)
        split = self.projector.evaluate(v_n, frame, 7)

        assert split[0] == direct[0]
        assert split[1] == direct[1]
        assert split[2] == direct[2]

    @pytest.mark.parametrize("d", DIMS)
    def test_frame_reused_across_many_stimuli(self, d):
        _, c_1, c_A, c_B = _inputs(d, 0)
        frame = self.projector.prepare(c_1, c_A, c_B)
        rng = np.random.default_rng(99)

        for i in range(50):
            v = rng.normal(size=d).astype(np.float64)
            v /= np.linalg.norm(v)
            assert self.projector.evaluate(v, frame, i) == self.projector.project(
                v, c_1, c_A, c_B, i
            )

    def test_frame_is_immutable(self):
        _, c_1, c_A, c_B = _inputs(384, 1)
        frame = self.projector.prepare(c_1, c_A, c_B)
        with pytest.raises(AttributeError):
            frame.v_dipole_norm_sq = 0.0

    def test_frame_fields_are_float64(self):
        _, c_1, c_A, c_B = _inputs(384, 2)
        frame = self.projector.prepare(c_1, c_A, c_B)
        assert isinstance(frame, PolarFrame)
        assert frame.c_1.dtype == np.float64
        assert frame.c1_hat.dtype == np.float64
        assert frame.v_dipole.dtype == np.float64
        assert type(frame.v_dipole_norm_sq) is float

    def test_prepare_accepts_non_float64_input(self):
        _, c_1, c_A, c_B = _inputs(384, 3)
        frame = self.projector.prepare(
            c_1.astype(np.float32), c_A.astype(np.float32), c_B.astype(np.float32)
        )
        assert frame.c_1.dtype == np.float64

    def test_lambda_is_exactly_python_float(self):
        v_n, c_1, c_A, c_B = _inputs(384, 4)
        _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, 0)
        assert type(lambda_val) is float
        assert type(d_esc) is float

    # --- Enforced preconditions ---

    @pytest.mark.parametrize("delta", [0.0, -0.1, -1.0])
    def test_init_rejects_non_positive_delta(self, delta):
        with pytest.raises(ValueError, match="delta"):
            PolarProjector(delta=delta)

    @pytest.mark.parametrize("eps", [0.0, -1e-9])
    def test_init_rejects_non_positive_eps_norm(self, eps):
        with pytest.raises(ValueError, match="eps_norm"):
            PolarProjector(eps_norm=eps)

    @pytest.mark.parametrize("eps", [0.0, -1e-6])
    def test_init_rejects_non_positive_eps_collinear(self, eps):
        with pytest.raises(ValueError, match="eps_collinear"):
            PolarProjector(eps_collinear=eps)

    def test_prepare_rejects_one_dimensional_space(self):
        one = np.array([1.0], dtype=np.float64)
        with pytest.raises(ValueError, match="d >= 2"):
            self.projector.prepare(one, one, one)

    def test_prepare_rejects_column_vector(self):
        """The silent-garbage case: (d,1) used to broadcast into a (d,d) matrix."""
        _, c_1, c_A, c_B = _inputs(384, 6)
        with pytest.raises(ValueError, match="1-D"):
            self.projector.prepare(c_1.reshape(-1, 1), c_A, c_B)

    def test_prepare_rejects_mismatched_pole_shapes(self):
        _, c_1, c_A, _ = _inputs(384, 7)
        c_B_short = np.ones(128, dtype=np.float64)
        with pytest.raises(ValueError, match="share shape"):
            self.projector.prepare(c_1, c_A, c_B_short)

    def test_prepare_rejects_underflowing_dipole(self):
        """delta so small that ||v_dipole||^2 underflows to zero in float64."""
        _, c_1, _, _ = _inputs(384, 8)
        projector = PolarProjector(delta=1e-200)
        with pytest.raises(ValueError, match="underflow"):
            projector.prepare(c_1, c_1 * 2.0, c_1 * 0.5)

    def test_evaluate_rejects_dimension_mismatch(self):
        _, c_1, c_A, c_B = _inputs(384, 9)
        frame = self.projector.prepare(c_1, c_A, c_B)
        with pytest.raises(ValueError, match="does not match"):
            self.projector.evaluate(np.ones(128, dtype=np.float64), frame, 0)

    def test_project_rejects_column_vector_instead_of_returning_garbage(self):
        v_n, c_1, c_A, c_B = _inputs(384, 10)
        with pytest.raises(ValueError):
            self.projector.project(v_n, c_1.reshape(-1, 1), c_A, c_B, 0)

    @pytest.mark.parametrize("d", DIMS)
    def test_collinear_poles_frame_matches_project(self, d):
        v_n, c_1, _, _ = _inputs(d, 5)
        c_A = c_1 * 2.0
        c_B = c_1 * 0.5

        frame = self.projector.prepare(c_1, c_A, c_B)
        assert self.projector.evaluate(v_n, frame, 3) == self.projector.project(
            v_n, c_1, c_A, c_B, 3
        )
        assert np.linalg.norm(frame.v_dipole) == pytest.approx(2.0 * self.projector.delta)
