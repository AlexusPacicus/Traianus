import sqlite3
import os
import numpy as np
from sentence_transformers import SentenceTransformer

print("[Traianus] Loading SentenceTransformer model for geodetic extraction...")

# =====================================================================
# OFFLINE GUARD (audit M3): bootstrap is the first run that used to
# download the model from the HF Hub. With the offline guard it requires
# local prefetch; the geodetic extraction becomes reproducible and sovereign.
# =====================================================================
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def build_encoder():
    return SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)


model = build_encoder()
DB_PATH = "traianus.db"

NSM_PRIMES = [
    "something", "someone", "something happens",
    "do", "happen", "move", "there is",
    "be someone", "be something", "be in a place",
    "be far", "be near", "be inside",
    "be on", "be under", "be above",
    "be below", "be big", "be small",
    "be good", "be bad", "think",
    "know", "want", "feel",
    "see", "hear", "say",
    "word", "true", "not",
    "maybe", "can", "if",
    "because", "very", "more",
    "like", "kind of", "part of",
    "one", "two", "some",
    "all", "much", "little",
    "this", "the same", "other",
    "time", "now", "before",
    "after", "long time", "short time",
    "place", "here", "above",
    "below", "far", "near",
    "side", "inside", "touch",
]


def serialize_vector(vector: np.ndarray) -> bytes:
    return vector.astype(np.float64).tobytes()


def extract_pure_octagon():
    print(f"[Traianus] Vectorizing {len(NSM_PRIMES)} concepts. Generating symmetric space...")

    embeddings = model.encode(NSM_PRIMES)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors_l2 = embeddings / norms

    anchor_idx = NSM_PRIMES.index("something")
    selected_axes = [anchor_idx]

    for _ in range(7):
        min_max_overlap = float("inf")
        best_candidate = None

        for idx in range(len(vectors_l2)):
            if idx in selected_axes:
                continue

            similarities = [
                float(np.dot(vectors_l2[idx], vectors_l2[selected]))
                for selected in selected_axes
            ]
            maximum_overlap = max(similarities)

            if maximum_overlap < min_max_overlap:
                min_max_overlap = maximum_overlap
                best_candidate = idx

        if best_candidate is not None:
            selected_axes.append(best_candidate)

    print(f"[Traianus] Extraction completed. {len(selected_axes)} axes selected.")

    octagon_data = {}
    for rank, idx in enumerate(selected_axes):
        symbol = chr(0x25B2 + rank)
        tag = NSM_PRIMES[idx].upper().replace(" ", "_").replace("'", "")
        octagon_data[f"{symbol}_{tag}"] = {
            "symbol": symbol,
            "tag": f"_{tag}",
            "vector": vectors_l2[idx],
        }

    return octagon_data


def anchor_in_sqlite(octagon_data):
    print("[Traianus] Persisting geodetic baseline to SQLite...")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geodesic_axes (
            id TEXT PRIMARY KEY,
            simbolo TEXT NOT NULL,
            tag TEXT NOT NULL,
            vector_blob BLOB NOT NULL
        )
    """)

    # H4 (F2.3): the geodetic basis is a regenerable derived artifact.
    # DELETE is prohibited; re-anchoring uses INSERT OR IGNORE to avoid
    # destroying the existing basis when re-running bootstrap.
    for rank, (key, data) in enumerate(octagon_data.items()):
        axis_id = f"AXIS_{rank + 1}"
        cursor.execute(
            "INSERT OR IGNORE INTO geodesic_axes (id, simbolo, tag, vector_blob) VALUES (?, ?, ?, ?)",
            (axis_id, data["symbol"], data["tag"], serialize_vector(data["vector"])),
        )

    conn.commit()
    conn.close()

    print(f"[SUCCESS] Geodetic baseline of {len(octagon_data)} axes anchored.")


def main():
    """Entry point of `traianus-bootstrap`: extracts and anchors the geodetic baseline."""
    octagon = extract_pure_octagon()
    anchor_in_sqlite(octagon)


if __name__ == "__main__":
    main()
