"""Freeze the Spinoza corpus as a portable embedding artifact.

Derives 384D L2-normalized float32 vectors for the 2221 committed chunks using
the pinned offline encoder, and writes them alongside their part labels so
downstream analysis can run on numpy alone — no torch, no sentence-transformers,
no substrate DB.

Sources are committed artifacts only (`data/spinoza/part*_manifest.json`), never
an ephemeral `.data/` scratch DB, so the artifact is reproducible from this
repository at any later commit. Manifest digests and the output digest are
recorded in the provenance sidecar; a re-run that produces a different digest
means the encoder or the corpus moved, and the analysis that consumed the old
artifact must be re-derived rather than silently trusted.

Read-only against the repository, offline (HF_HUB_OFFLINE=1), deterministic for
a fixed encoder revision.

Usage:
    python3 tools/experiments/tooling/freeze_spinoza_embeddings.py
    python3 tools/experiments/tooling/freeze_spinoza_embeddings.py --out <dir>
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from traianus.representation.sentence_transformer import (
    MODEL_ID,
    MODEL_REVISION,
    SentenceTransformerProvider,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / "data" / "spinoza"

# Reading order of the Ethics; the part label is the ground-truth class used by
# downstream analysis, and is never itself embedded.
PARTS = (
    ("P1_GOD", "part1_god_manifest.json"),
    ("P2_MIND", "part2_mind_manifest.json"),
    ("P3_AFFECTS", "part3_affects_manifest.json"),
    ("P4_BONDAGE", "part4_bondage_manifest.json"),
    ("P5_POWER", "part5_power_manifest.json"),
)

EXPECTED_COUNTS = {
    "P1_GOD": 409,
    "P2_MIND": 458,
    "P3_AFFECTS": 627,
    "P4_BONDAGE": 507,
    "P5_POWER": 220,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_corpus() -> tuple[list[str], list[str], list[str], dict[str, str]]:
    """Return (labels, parts, texts, manifest digests) in reading order."""
    labels: list[str] = []
    parts: list[str] = []
    texts: list[str] = []
    digests: dict[str, str] = {}

    for part, filename in PARTS:
        path = CORPUS_DIR / filename
        manifest = json.loads(path.read_text(encoding="utf-8"))
        digests[filename] = _sha256(path)

        if len(manifest) != EXPECTED_COUNTS[part]:
            raise SystemExit(
                f"ERR: {filename} holds {len(manifest)} chunks, expected "
                f"{EXPECTED_COUNTS[part]}. The corpus moved since the telemetry "
                f"this artifact is meant to be comparable against (v5, 2221 nodes); "
                f"re-derive that telemetry before freezing new embeddings."
            )

        # Python 3.7+ dicts preserve insertion order, and the builder writes
        # insertion order == reading order (data/spinoza/PROVENANCE.md).
        for label, text in manifest.items():
            labels.append(label)
            parts.append(part)
            texts.append(text)

    return labels, parts, texts, digests


def embed(texts: list[str]) -> np.ndarray:
    """Encode, L2-normalize and downcast to the substrate's float32 contract."""
    provider = SentenceTransformerProvider()
    raw = np.asarray(provider.encode_batch(texts), dtype=np.float64)

    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    if not np.all(norms > 0.0):
        degenerate = int(np.count_nonzero(norms <= 0.0))
        raise SystemExit(f"ERR: {degenerate} chunk(s) encoded to a zero vector")

    return (raw / norms).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / ".data" / "spinoza_frozen",
        help="output directory (default: .data/spinoza_frozen, gitignored)",
    )
    args = parser.parse_args()

    labels, parts, texts, manifest_digests = load_corpus()
    print(f"corpus: {len(texts)} chunks across {len(PARTS)} parts")

    print(f"encoding with {MODEL_ID}@{MODEL_REVISION[:12]} (offline)...")
    vectors = embed(texts)

    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    print(
        f"vectors: {vectors.shape} {vectors.dtype}; "
        f"||v||_2 in [{norms.min():.9f}, {norms.max():.9f}]"
    )

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    vectors_path = out_dir / "embeddings.npy"
    labels_path = out_dir / "labels.json"
    provenance_path = out_dir / "PROVENANCE.json"

    np.save(vectors_path, vectors)
    labels_path.write_text(
        json.dumps(
            [{"label": lab, "part": part} for lab, part in zip(labels, parts, strict=True)],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    provenance = {
        "source": "data/spinoza/part*_manifest.json (committed artifacts only)",
        "builder": "tools/experiments/tooling/freeze_spinoza_embeddings.py",
        "encoder": {"model_id": MODEL_ID, "revision": MODEL_REVISION, "offline": True},
        "representation": "384D, L2-normalized, float32",
        "n_chunks": len(texts),
        "chunks_per_part": EXPECTED_COUNTS,
        "manifest_sha256": manifest_digests,
        "embeddings_sha256": _sha256(vectors_path),
        "labels_sha256": _sha256(labels_path),
        "comparable_telemetry": "data/spinoza/telemetry/v5.json (accumulated_12345, 2221 nodes)",
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {vectors_path} ({vectors.nbytes / 1024:.0f} KiB)")
    print(f"wrote {labels_path}")
    print(f"wrote {provenance_path}")
    print(f"embeddings sha256: {provenance['embeddings_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
