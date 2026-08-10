"""
Exporter of the real geodetic basis (NSM octagon) to frozen JSON.

Phase 0 (Foundations). Produces `tests/fixtures/nsm_axes_8.json`: REALISTIC
(not one-hot) geometry derived from the cached all-MiniLM-L6-v2 model
(off-diagonal cosine ≈ 0.23, max ≈ 0.34, measured by audit C1).

Hermetic tests seed this geometry with
`helpers.db_factory.seed_realistic_axes` WITHOUT reloading the model (L1).

Usage:
    HF_HUB_OFFLINE=1 python tools/experiments/export_nsm_axes.py [tests/fixtures/nsm_axes_8.json]
"""
import json
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, os.path.abspath("."))

from traianus import bootstrap  # noqa: E402


def export_octagon() -> list[dict]:
    """Extracts the real geodetic octagon and serializes it to JSON."""
    octagon = bootstrap.extract_pure_octagon()
    payload = []
    for rank, key in enumerate(octagon):
        data = octagon[key]
        payload.append({
            "id": f"AXIS_{rank + 1}",
            "simbolo": data["symbol"],
            "tag": data["tag"],
            "vector": [float(x) for x in data["vector"]],
        })
    return payload


def main(out_path: str = "tests/fixtures/nsm_axes_8.json") -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    payload = export_octagon()
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"[export_nsm_axes] {len(payload)} axes exported to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/nsm_axes_8.json")
