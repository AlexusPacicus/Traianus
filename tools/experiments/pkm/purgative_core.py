"""
PKM experiment — tools/experiments/pkm/purgative_core.py.

Origin: NotebookLM experimentation notebook (personal-knowledge-management
packaging). NOT a Traianus substrate contract.

The 64-byte <ffffff32s8x layout, the .purgativa stream, CLINICAL_REGEX
sanitation, and Arrhenius/MTBF thermodynamics are a portable knowledge
packaging format for local-first PKM. They are independent of the 384D
substrate in traianus/ (which stores float64 vectors) and of the render
loop, which consumes semantic projections (projections_json).

Explicitly NOT canonical: no mirror of traianus/storage.py. The render and
store must not read/write this 64B struct on the hot path.
"""
import numpy as np
import struct
import re
from scipy.spatial.distance import pdist, squareform
from scipy.sparse.csgraph import connected_components

FLOAT_DTYPE = np.float64
LATENT_DIM = 384
MAX_ID_BYTES = 32
STRUCT_FORMAT = f'<ffffff{MAX_ID_BYTES}s8x'
STRUCT_PACKER = struct.Struct(STRUCT_FORMAT)
EPSILON = 1e-8

XYZ_DIMS = 3
COLOR_DIMS = 3
TOTAL_REQUIRED_DIMS = XYZ_DIMS + COLOR_DIMS

OKLCH_L_MIN, OKLCH_L_RANGE = 0.3, 0.6
OKLCH_C_MIN, OKLCH_C_RANGE = 0.05, 0.25
OKLCH_H_MAX = 360.0

BOLTZMANN_EV = 8.6173e-5
ACTIVATION_ENERGY_EV = 0.7
TEMP_IDLE_KELVIN = 313.15
THERMAL_JOULE_SCALING = 25.0
NOMINAL_MTBF_HOURS = 50000.0
DEFAULT_H0_THRESHOLD = 1.2


def safe_utf8_truncate(text: str, max_bytes: int = 32) -> bytes:
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return encoded.ljust(max_bytes, b'\x00')
    truncated = encoded[:max_bytes]
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    if truncated and (truncated[-1] & 0x80) != 0:
        truncated = truncated[:-1]
    return truncated.ljust(max_bytes, b'\x00')


class TraianusPurgativeCore:
    def __init__(self, num_nodes=50, seed=42):
        self.rng = np.random.default_rng(seed)
        self.num_nodes = num_nodes
        self.dim_actual = 2
        self.raw_nodes = self.rng.normal(0.0, 1.0, (num_nodes, LATENT_DIM)).astype(FLOAT_DTYPE)
        self.clinical_regex = re.compile(
            r'\b(tdah|adhd|ansiedad|depresi[oó]n|trastorno|paciente|diagn[oó]stico)\b',
            re.IGNORECASE
        )

    def sanitize_somatic_flow(self, text):
        if self.clinical_regex.search(text):
            return self.clinical_regex.sub('[Estímulo Somático Desplazado]', text), True
        return text, False

    def process_geometry_and_color(self, matrix):
        mean_vec = np.mean(matrix, axis=0)
        centered = matrix - mean_vec
        _, _, Vt = np.linalg.svd(centered, full_matrices=False)
        anisotropy_dir = Vt[0]
        purified = centered - np.outer(np.dot(centered, anisotropy_dir), anisotropy_dir)
        if Vt.shape[0] < TOTAL_REQUIRED_DIMS:
            pad_size = TOTAL_REQUIRED_DIMS - Vt.shape[0]
            Vt = np.vstack([Vt, np.zeros((pad_size, Vt.shape[1]), dtype=FLOAT_DTYPE)])
        xyz = np.dot(purified, Vt[:XYZ_DIMS].T)
        lch_raw = np.dot(purified, Vt[XYZ_DIMS:TOTAL_REQUIRED_DIMS].T)
        L = OKLCH_L_MIN + OKLCH_L_RANGE * ((lch_raw[:, 0] - lch_raw[:, 0].min()) / (np.ptp(lch_raw[:, 0]) + EPSILON))
        C = OKLCH_C_MIN + OKLCH_C_RANGE * ((lch_raw[:, 1] - lch_raw[:, 1].min()) / (np.ptp(lch_raw[:, 1]) + EPSILON))
        H = OKLCH_H_MAX * ((lch_raw[:, 2] - lch_raw[:, 2].min()) / (np.ptp(lch_raw[:, 2]) + EPSILON))
        return purified, xyz, np.column_stack((L, C, H))

    def evaluate_h0_pulsation(self, purified_matrix, threshold=DEFAULT_H0_THRESHOLD):
        dist_matrix = squareform(pdist(purified_matrix, metric='euclidean'))
        adj_matrix = (dist_matrix < threshold).astype(int)
        n_islands, _ = connected_components(adj_matrix, directed=False)
        pulsated = False
        if n_islands > self.dim_actual:
            self.dim_actual = n_islands
            pulsated = True
        return n_islands, pulsated

    def execute_purgative_pass(self, joules_per_token=0.35):
        purified, xyz, lch = self.process_geometry_and_color(self.raw_nodes)
        temp_k = TEMP_IDLE_KELVIN + (joules_per_token * THERMAL_JOULE_SCALING)
        af = np.exp((ACTIVATION_ENERGY_EV / BOLTZMANN_EV) * ((1.0 / TEMP_IDLE_KELVIN) - (1.0 / temp_k)))
        mtbf_hours = NOMINAL_MTBF_HOURS / af
        n_islands, pulsated = self.evaluate_h0_pulsation(purified)
        return {
            "purified_matrix": purified, "xyz": xyz, "lch": lch,
            "temp_k": temp_k, "mtbf_hours": mtbf_hours,
            "n_islands": n_islands, "pulsated": pulsated
        }

    def serialize_zero_copy(self, idx, xyz, lch, raw_id):
        sanitized_id, _ = self.sanitize_somatic_flow(raw_id)
        id_bytes = safe_utf8_truncate(sanitized_id, MAX_ID_BYTES)
        return STRUCT_PACKER.pack(
            float(xyz[idx, 0]), float(xyz[idx, 1]), float(xyz[idx, 2]),
            float(lch[idx, 0]), float(lch[idx, 1]), float(lch[idx, 2]),
            id_bytes
        )

if __name__ == "__main__":
    core = TraianusPurgativeCore(num_nodes=30)
    res = core.execute_purgative_pass()
    print("✅ Núcleo local inicializado correctamente.")
    print(f"Verificación: {res['n_islands']} islas H0 detectadas.")
