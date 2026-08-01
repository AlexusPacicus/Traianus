"""
G9 — Zero-Trust TridenGuard (AGENTS.md §2.3, README_CODE_ENGINE.md).

Normative (RFC 2119): the TridenGuard gate MUST block any
fragment with fetch/axios/urllib.request/import requests (ABORTED_VIOLATES_
ZERO_TRUST), MUST block Safety_Abort != NONE (BLOCKED_BY_SAFETY_GATE),
and MUST verify literal grounding (character by character) for
REFACTOR/FIX/AUDIT (ABORTED_GROUNDING_FAILED).

Normative: docs/development/tests/SPEC-global.md
Coverage: G9
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("tools"))
from tridenguard_validator import validate_proposal  # noqa: E402

from helpers.endpoint_registry import BLOCKS


@pytest.mark.parametrize("block", BLOCKS)
def test_g9_blocks_network_access(block):
    """MUST: fetch/axios/urllib.request/requests are blocked."""
    for token in ["fetch(", "axios", "urllib.request", "import requests"]:
        proposal = {
            "Intent_Class": "REFACTOR",
            "Implementation_Block": f"const x = {token}(...)",
            "Topological_Grounding": "grounding",
            "Safety_Abort": "NONE",
        }
        decision = validate_proposal(json.dumps(proposal), "")
        assert decision["status"] == "QUARANTINED", token
        assert decision["final_decision"] == "ABORTED_VIOLATES_ZERO_TRUST", token


@pytest.mark.parametrize("block", BLOCKS)
def test_g9_safety_abort_blocks(block):
    """MUST: Safety_Abort != NONE blocks the proposal."""
    proposal = {
        "Intent_Class": "REFACTOR",
        "Implementation_Block": "safe code",
        "Topological_Grounding": "grounding",
        "Safety_Abort": "FORCED_ABORT",
    }
    decision = validate_proposal(json.dumps(proposal), "")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"


@pytest.mark.parametrize("block", BLOCKS)
def test_g9_grounding_literal(block):
    """MUST: for REFACTOR/FIX/AUDIT, citation must exist character by character."""
    target = os.path.abspath("traianus/app.py")
    present = "def auto_calibrate_critical_threshold() -> float:"
    absent = "this citation does not exist in the source file"

    ok = validate_proposal(
        json.dumps({
            "Intent_Class": "FIX",
            "Implementation_Block": "patch",
            "Topological_Grounding": present,
            "Safety_Abort": "NONE",
        }),
        target,
    )
    assert ok["status"] == "VALIDATED"
    assert ok["final_decision"] == "EXECUTE_SAFE"

    bad = validate_proposal(
        json.dumps({
            "Intent_Class": "FIX",
            "Implementation_Block": "patch",
            "Topological_Grounding": absent,
            "Safety_Abort": "NONE",
        }),
        target,
    )
    assert bad["status"] == "QUARANTINED"
    assert bad["final_decision"] == "ABORTED_GROUNDING_FAILED"
