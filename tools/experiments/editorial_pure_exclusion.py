"""Editorial pure-exclusion check: do the 11 pure editorial footnote chunks change K6, R4 or Z?

Implements the delegation contract editorial-pure-exclusion-check (B1-B8). 17 Gutenberg footnote blocks
leaked into the frozen Spinoza corpus; data/spinoza/editorial_marks.json marks 25 labels, 11 of them pure
(the whole chunk is editorial footnote text) and 14 mixed (Spinoza's text with a footnote residue). This
runner drops the 11 pure chunks, re-runs K6, R4 and Z through their own run() functions on the filtered
corpus, and compares each result with the committed one under the rule below, fixed before any result
exists. Labelled exploration (docs/methodology/METHODOLOGY.md "Explore"): no audit record, no blind review,
never enters the registry.

Comparison rule (verbatim, B4): `unchanged` is true iff every DECIDING field is equal; reported fields never
decide. K6: deciding = `valid` and `selected` (same channel names in the same order); reported = n_fit,
n_eval, ranking_fit, means_fit, failed_conditions, positive_control.margin. R4: deciding = `valid` and
`r4_holds`; reported = margin, n, reported.l_gt.value, reported.l_gt.interval, failed_conditions. Z, with two
filtered runs: deciding = `valid`, z1.decision and z2.decision; the two runs must be equal, parsed as JSON,
in every key outside `z2`, otherwise the Z comparison is `usable: false` and no decision is used; the
filtered z2.decision is used only if both runs give the same z2 decision, otherwise z2 is reported
`not reproducible` and unchanged is false for Z with that reason; reported = z1.n, z1.d_bar_cells_agree,
z2.median_delta_ns, z2.ready_p95_ns, z2.per_l of both runs, failed_conditions. A missing key in a filtered
result is a difference, not an exception.

No thresholds or tolerances are invented here: every comparison above is field equality on parsed JSON.

Refuses to run (writing nothing) unless the local artefacts match the frozen corpus's pinned digests
(k6.IntegrityError) or the 11 pure labels are all present, once each, in the corpus (ValueError); a filtered
measurement that is itself invalid is still written and reported as changed.

Usage:
    python3 tools/experiments/editorial_pure_exclusion.py [--out-dir DIR] [--work-dir DIR]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import io
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import r4_perspective_recall as r4
from tools.experiments import zoom_three_point as zoom

MARKS = REPO_ROOT / "data" / "spinoza" / "editorial_marks.json"
WORK_DIR = REPO_ROOT / ".data" / "spinoza_no_pure_notes"
OUT_DIR = REPO_ROOT / "data" / "refapp" / "editorial_pure_exclusion"

_MISSING = object()


# Corpus (B1, B2, B3) --------------------------------------------------------------------------------


def pure_labels(marks: Mapping[str, Any]) -> list[str]:
    """B1: the sorted labels of `marks["marked"]` whose `pure` is exactly true; mixed labels are not returned."""
    marked = marks["marked"]
    return sorted(label for label, info in marked.items() if info.get("pure") is True)


def filter_corpus(
    embeddings: NDArray[np.float32], labels: Sequence[Mapping[str, str]], drop: Sequence[str]
) -> tuple[NDArray[np.float32], list[Mapping[str, str]]]:
    """B2: embeddings and labels without the rows named in `drop`, order kept, rows and label objects unchanged."""
    if len(embeddings) != len(labels):
        raise ValueError(f"row count {len(embeddings)} != label count {len(labels)}")
    counts = Counter(item["label"] for item in labels)
    for label in drop:
        if counts[label] == 0:
            raise ValueError(f"label {label!r} not found in labels")
        if counts[label] > 1:
            raise ValueError(f"label {label!r} appears more than once in labels")
    drop_set = set(drop)
    keep = [i for i, item in enumerate(labels) if item["label"] not in drop_set]
    kept_embeddings = np.ascontiguousarray(np.asarray(embeddings, dtype="<f4")[keep])
    kept_labels = [labels[i] for i in keep]
    return kept_embeddings, kept_labels


def write_filtered_inputs(
    work_dir: Path, embeddings: NDArray[np.float32], labels: Sequence[Mapping[str, str]]
) -> tuple[Path, Path, dict[Path, str]]:
    """B3: embeddings.npy (np.save, no pickle) and labels.json (UTF-8 JSON) written into work_dir; returns the
    two paths and the sha256 hex digest of the bytes actually written."""
    work_dir.mkdir(parents=True, exist_ok=True)
    embeddings_path = work_dir / "embeddings.npy"
    labels_path = work_dir / "labels.json"
    buffer = io.BytesIO()
    np.save(buffer, np.ascontiguousarray(embeddings, dtype="<f4"), allow_pickle=False)
    embeddings_bytes = buffer.getvalue()
    labels_bytes = json.dumps(list(labels)).encode("utf-8")
    embeddings_path.write_bytes(embeddings_bytes)
    labels_path.write_bytes(labels_bytes)
    digests = {
        embeddings_path: hashlib.sha256(embeddings_bytes).hexdigest(),
        labels_path: hashlib.sha256(labels_bytes).hexdigest(),
    }
    return embeddings_path, labels_path, digests


# Comparison (B4) -------------------------------------------------------------------------------------


def _field(d: Mapping[str, Any], path: str) -> Any:
    """The value at a dotted path, or the module's MISSING sentinel if any level is absent."""
    node: Any = d
    for part in path.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _present(value: Any) -> Any:
    return "<missing>" if value is _MISSING else value


def _pair(committed: Mapping[str, Any], filtered: Mapping[str, Any], path: str) -> dict[str, Any]:
    return {"committed": _present(_field(committed, path)), "filtered": _present(_field(filtered, path))}


def _both(run1: Mapping[str, Any], run2: Mapping[str, Any], path: str) -> dict[str, Any]:
    return {"run1": _present(_field(run1, path)), "run2": _present(_field(run2, path))}


def _changed_fields(fields: Sequence[str], committed: Mapping[str, Any], filtered: Mapping[str, Any]) -> list[str]:
    return [f for f in fields if _field(committed, f) != _field(filtered, f)]


def _decision_reason(fields: Sequence[str], committed: Mapping[str, Any], filtered: Mapping[str, Any]) -> str:
    changed = _changed_fields(fields, committed, filtered)
    reason = ", ".join(f"{f} changed" for f in changed)
    if "valid" in changed:
        reason += f"; filtered failed_conditions={filtered.get('failed_conditions')!r}"
    return reason


def _equal_outside(a: Mapping[str, Any], b: Mapping[str, Any], exclude: set[str]) -> bool:
    return {k: v for k, v in a.items() if k not in exclude} == {k: v for k, v in b.items() if k not in exclude}


K6_DECIDING = ("valid", "selected")
K6_REPORTED = ("n_fit", "n_eval", "ranking_fit", "means_fit", "failed_conditions", "positive_control.margin")
R4_DECIDING = ("valid", "r4_holds")
R4_REPORTED = ("margin", "n", "reported.l_gt.value", "reported.l_gt.interval", "failed_conditions")
Z_CORE_DECIDING = ("valid", "z1.decision")
Z_REPORTED = ("z1.n", "z1.d_bar_cells_agree", "z2.median_delta_ns", "z2.ready_p95_ns", "z2.per_l")


def compare_k6(committed: Mapping[str, Any], filtered: Mapping[str, Any]) -> dict[str, Any]:
    """K6's decision is `valid` and `selected` (same channels, same order); every other field is reported only."""
    deciding = {f: _pair(committed, filtered, f) for f in K6_DECIDING}
    unchanged = not _changed_fields(K6_DECIDING, committed, filtered)
    reported = {f: _pair(committed, filtered, f) for f in K6_REPORTED}
    reason = None if unchanged else _decision_reason(K6_DECIDING, committed, filtered)
    return {"unchanged": unchanged, "deciding": deciding, "reported": reported, "reason": reason}


def compare_r4(committed: Mapping[str, Any], filtered: Mapping[str, Any]) -> dict[str, Any]:
    """R4's decision is `valid` and `r4_holds`; every other field is reported only."""
    deciding = {f: _pair(committed, filtered, f) for f in R4_DECIDING}
    unchanged = not _changed_fields(R4_DECIDING, committed, filtered)
    reported = {f: _pair(committed, filtered, f) for f in R4_REPORTED}
    reason = None if unchanged else _decision_reason(R4_DECIDING, committed, filtered)
    return {"unchanged": unchanged, "deciding": deciding, "reported": reported, "reason": reason}


def compare_z(committed: Mapping[str, Any], filtered_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Z's decision is `valid`, z1.decision and z2.decision. The two filtered runs must first agree outside `z2`
    (usable); z1 and the top-level fields are then read from run 1, since usable guarantees they equal run 2's.
    z2.decision is used only if both runs agree on it (z2_reproducible); otherwise it is reported
    'not reproducible' and the comparison is unchanged=false for that reason. Every reported figure is read from
    both runs, since `z2`'s other fields are not covered by the usable check."""
    run1, run2 = filtered_results
    usable = _equal_outside(run1, run2, {"z2"})
    reported = {field: _both(run1, run2, field) for field in Z_REPORTED}
    reported["failed_conditions"] = _both(run1, run2, "failed_conditions")
    if not usable:
        return {
            "unchanged": False,
            "usable": False,
            "z2_reproducible": None,
            "deciding": {},
            "reported": reported,
            "reason": "the two filtered Z runs differ outside z2: usable is false, no decision is used",
        }
    z2_reproducible = _field(run1, "z2.decision") == _field(run2, "z2.decision")
    deciding = {f: _pair(committed, run1, f) for f in Z_CORE_DECIDING}
    if z2_reproducible:
        deciding["z2.decision"] = _pair(committed, run1, "z2.decision")
    else:
        deciding["z2.decision"] = {
            "committed": _present(_field(committed, "z2.decision")), "filtered": "not reproducible",
        }
    core_changed = _changed_fields(Z_CORE_DECIDING, committed, run1)
    z2_changed = z2_reproducible and _field(committed, "z2.decision") != _field(run1, "z2.decision")
    unchanged = not core_changed and z2_reproducible and not z2_changed
    reason = None
    if not unchanged:
        parts = []
        if core_changed:
            parts.append(_decision_reason(Z_CORE_DECIDING, committed, run1))
        if not z2_reproducible:
            parts.append("z2 decision not reproducible across the two filtered runs")
        elif z2_changed:
            parts.append("z2.decision changed")
        reason = "; ".join(parts)
    return {
        "unchanged": unchanged, "usable": True, "z2_reproducible": z2_reproducible,
        "deciding": deciding, "reported": reported, "reason": reason,
    }


# Null control (B5) ----------------------------------------------------------------------------------


def run_control(work_dir: Path) -> dict[str, Any]:
    """k6.run and r4.run on the unfiltered artefacts, each compared with the committed result outside
    `environment`; usable is true iff both agree."""
    work_dir.mkdir(parents=True, exist_ok=True)
    k6_out = k6.run(k6.EMBEDDINGS, k6.LABELS, k6.AXES, k6.EXPECTED_DIGESTS, work_dir / "control_k6.json")
    r4_out = r4.run(k6.EMBEDDINGS, k6.LABELS, k6.AXES, k6.RESULT, r4.EXPECTED_DIGESTS, work_dir / "control_r4.json")
    committed_k6 = json.loads(k6.RESULT.read_text(encoding="utf-8"))
    committed_r4 = json.loads(r4.RESULT.read_text(encoding="utf-8"))
    k6_equal = _equal_outside(committed_k6, k6_out, {"environment"})
    r4_equal = _equal_outside(committed_r4, r4_out, {"environment"})
    return {"usable": k6_equal and r4_equal, "k6_equal": k6_equal, "r4_equal": r4_equal}


# Orchestration (B6, B7, B8) --------------------------------------------------------------------------


def _write(payload: Mapping[str, Any], out_path: Path) -> dict[str, Any]:
    text = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def run(work_dir: Path = WORK_DIR, out_dir: Path = OUT_DIR) -> dict[str, Any]:
    """B6-B8: drop the 11 pure labels, run the null control, then K6, R4 and Z (twice) on the filtered corpus,
    each through its own run(); compare every filtered result with the committed one and write comparison.json.
    An IntegrityError from check_digests or a ValueError from filter_corpus raises before anything is written
    to out_dir; a measurement whose filtered run is itself invalid is still written and compared."""
    marks = json.loads(MARKS.read_text(encoding="utf-8"))
    drop = pure_labels(marks)
    raw = k6.check_digests({
        k6.EMBEDDINGS: k6.EXPECTED_DIGESTS[k6.EMBEDDINGS], k6.LABELS: k6.EXPECTED_DIGESTS[k6.LABELS],
    })
    embeddings = np.load(io.BytesIO(raw[k6.EMBEDDINGS]), allow_pickle=False)
    labels = json.loads(raw[k6.LABELS].decode("utf-8"))
    n_before = len(labels)
    filtered_embeddings, filtered_labels = filter_corpus(embeddings, labels, drop)
    n_after = len(filtered_labels)
    embeddings_path, labels_path, digests = write_filtered_inputs(work_dir, filtered_embeddings, filtered_labels)
    filtered_expected = {**digests, k6.AXES: k6.EXPECTED_DIGESTS[k6.AXES]}

    control = run_control(work_dir)

    k6_json_path = out_dir / "k6.json"
    k6_filtered = k6.run(embeddings_path, labels_path, k6.AXES, filtered_expected, k6_json_path)

    k6_json_digest = hashlib.sha256(k6_json_path.read_bytes()).hexdigest()
    r4_expected = {**filtered_expected, k6_json_path: k6_json_digest}
    r4_filtered = r4.run(embeddings_path, labels_path, k6.AXES, k6_json_path, r4_expected, out_dir / "r4.json")

    z_run1 = zoom.run(zoom.K6_FILE, embeddings_path, labels_path, k6.AXES, filtered_expected, out_dir / "z_run1.json")
    z_run2 = zoom.run(zoom.K6_FILE, embeddings_path, labels_path, k6.AXES, filtered_expected, out_dir / "z_run2.json")

    committed_k6 = json.loads(k6.RESULT.read_text(encoding="utf-8"))
    committed_r4 = json.loads(r4.RESULT.read_text(encoding="utf-8"))
    committed_z = json.loads(zoom.RESULT.read_text(encoding="utf-8"))

    k6_cmp = compare_k6(committed_k6, k6_filtered)
    r4_cmp = compare_r4(committed_r4, r4_filtered)
    z_cmp = compare_z(committed_z, (z_run1, z_run2))

    comparison = {
        "dropped": sorted(drop),
        "n_before": n_before,
        "n_after": n_after,
        "digests": {p.name: d for p, d in digests.items()},
        "control": control,
        "k6": k6_cmp,
        "r4": r4_cmp,
        "z": z_cmp,
        "changed": [name for name, cmp in (("K6", k6_cmp), ("R4", r4_cmp), ("Z", z_cmp)) if not cmp["unchanged"]],
    }
    return _write(comparison, out_dir / "comparison.json")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="K6, R4 and Z without the 11 pure editorial chunks.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help=f"output directory (default: {OUT_DIR})")
    parser.add_argument("--work-dir", type=Path, default=WORK_DIR, help=f"working directory (default: {WORK_DIR})")
    args = parser.parse_args(argv)
    try:
        result = run(args.work_dir, args.out_dir)
    except (k6.IntegrityError, ValueError) as exc:
        print(str(exc))
        raise SystemExit(1) from exc
    print(f"control: {'usable' if result['control']['usable'] else 'not usable'}")
    for key, name in (("k6", "K6"), ("r4", "R4"), ("z", "Z")):
        print(f"{name}: {'unchanged' if result[key]['unchanged'] else 'changed'}")


if __name__ == "__main__":
    main()
