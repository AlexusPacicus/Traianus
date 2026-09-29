"""Pure minimum spanning tree over the current nodes (observational, numpy only)."""

import numpy as np


def compute_minimum_spanning_tree(nodes: dict[str, np.ndarray]) -> list[dict]:
    """Pure minimum spanning tree of the complete L2 graph over the nodes: no DB access.

    Prim over the ids in sorted order, from the first id. Ties go to the lower
    sorted position, and a key is replaced only by a strictly smaller distance,
    so ties keep the earlier parent. Lengths are computed and rounded as
    compute_epsilon_edges does. Edges are sorted by (source, target); none for
    fewer than two nodes.
    """
    ids = sorted(nodes)
    n = len(ids)
    if n < 2:
        return []
    matrix = np.stack([nodes[i] for i in ids])
    joined = np.zeros(n, dtype=bool)
    joined[0] = True
    best = np.linalg.norm(matrix - matrix[0], axis=1)
    parent = np.zeros(n, dtype=np.intp)
    edges: list[dict] = []
    for _ in range(n - 1):
        j = int(np.argmin(np.where(joined, np.inf, best)))
        joined[j] = True
        a, b = sorted((int(parent[j]), j))
        edges.append({
            "source": ids[a],
            "target": ids[b],
            "distance": round(float(np.linalg.norm(nodes[ids[a]] - nodes[ids[b]])), 6),
        })
        row = np.linalg.norm(matrix - matrix[j], axis=1)
        closer = ~joined & (row < best)
        best[closer] = row[closer]
        parent[closer] = j
    edges.sort(key=lambda e: (e["source"], e["target"]))
    return edges
