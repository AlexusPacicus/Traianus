"""
Structure guardians — Spec-First and 1:1 traceability (Phase 3).

Normative: docs/archive/legacy_docs/development/tests/SPEC-template.md
Coverage: (the guardians verify the rest of the harness; they themselves are
the meta-traceability tool, they do not implement domain requirements).
"""
import ast
import os

import pytest

from tests.meta._spec_lib import (
    ACTIVE_SPECS,
    EXCLUDED_DIRS,
    ROOT,
    SPEC_FILES,
    has_rfc2119_keyword,
    iter_test_files,
    norm_id,
    parse_header_ids,
    parse_spec_ids,
    read_header,
)

TESTS_ROOT = os.path.join(ROOT, "tests")


def _normative_target(header: str) -> set[str]:
    """SPECs referenced by 'Normative:' in the header."""
    return parse_header_ids(header, prefix="Normative:")


# ---------------------------------------------------------------------------
# 1. SPECs exist, are canonical and parse.
# ---------------------------------------------------------------------------


def test_specs_exist_and_parse():
    for spec_name in SPEC_FILES:
        ids = parse_spec_ids(spec_name)
        assert len(ids) >= 1, f"{spec_name} without normative IDs"
        assert len(ids) == len({norm_id(i) for i in ids}), f"{spec_name}: duplicate IDs"


# ---------------------------------------------------------------------------
# 2. Every test file has a normative header (Normative + Coverage + RFC 2119).
# ---------------------------------------------------------------------------


def test_every_test_file_has_normative_header():
    offenders = []
    for path in iter_test_files(TESTS_ROOT):
        header = read_header(path)
        if "Normative:" not in header or "Coverage:" not in header:
            offenders.append(f"{path}: missing Normative/Coverage")
        elif not has_rfc2119_keyword(header):
            offenders.append(f"{path}: missing RFC 2119 keyword (MUST/MUST NOT/SHOULD)")
    assert not offenders, "\n".join(offenders)


# ---------------------------------------------------------------------------
# 3. 1:1 MUST <-> test: each canonical ID is covered by exactly one file;
#    no gaps and no invented IDs.
# ---------------------------------------------------------------------------


def test_each_must_has_exactly_one_covering_file():
    for spec_name in ACTIVE_SPECS:
        canonical = {norm_id(i) for i in parse_spec_ids(spec_name)}
        declared: dict[str, list[str]] = {}
        for path in iter_test_files(TESTS_ROOT):
            header = read_header(path)
            target = _normative_target(header)
            covers = any(
                t == spec_name or t.endswith(SPEC_FILES[spec_name]) for t in target
            )
            if not covers:
                continue
            covered = {norm_id(i) for i in parse_header_ids(header)}
            for cid in covered:
                declared.setdefault(cid, []).append(path)

        missing = canonical - set(declared)
        duplicated = {cid: paths for cid, paths in declared.items() if len(paths) > 1}
        invented = set(declared) - canonical
        assert not missing, f"{spec_name}: MUST without test -> {sorted(missing)}"
        assert not duplicated, f"{spec_name}: MUST with >1 file -> {duplicated}"
        assert not invented, f"{spec_name}: non-canonical IDs -> {sorted(invented)}"


# ---------------------------------------------------------------------------
# 4. No orphan tests: each function references an ID from its Coverage.
# ---------------------------------------------------------------------------


def test_no_test_function_is_orphan():
    orphans = []
    for path in iter_test_files(TESTS_ROOT):
        header = read_header(path)
        covered = {norm_id(i) for i in parse_header_ids(header)}
        if not covered:
            orphans.append(f"{path}: empty Coverage")
            continue
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                doc = ast.get_docstring(node) or ""
                haystack = norm_id(node.name) + norm_id(doc)
                if not any(cid in haystack for cid in covered):
                    orphans.append(f"{path}::{node.name} does not reference any Coverage ID")
    assert not orphans, "\n".join(orphans)


def test_generics_registry_is_well_formed():
    """Every block references only defined generics; the catalog is G1-G9.

    This is the non-tautological counterpart of the per-block
    `*_generics_registry_matches` tests: it guards the REGISTRY structure
    (no unknown blocks, no invented generics) instead of mirroring a literal.
    """
    from helpers.endpoint_registry import BLOCKS, GENERIC_DEFINITIONS, GENERICS_BY_BLOCK

    defined = set(GENERIC_DEFINITIONS)
    assert defined == {f"G{i}" for i in range(1, 10)}, (
        f"GENERIC_DEFINITIONS catalog must be exactly G1..G9, got {sorted(defined)}"
    )
    assert len(BLOCKS) == len(set(BLOCKS)), "BLOCKS must not contain duplicates"
    for block, generics in GENERICS_BY_BLOCK.items():
        assert block in BLOCKS, f"unknown block {block!r} in GENERICS_BY_BLOCK"
        assert set(generics) <= defined, (
            f"block {block!r} references undefined generic(s): {set(generics) - defined}"
        )
