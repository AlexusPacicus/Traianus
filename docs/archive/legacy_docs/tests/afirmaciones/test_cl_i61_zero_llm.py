"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-I61 (ADR-016): the control plane does not invoke generative LLMs
(zero-LLM). It only uses SentenceTransformer as a deterministic embedding
provider (not generative).
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-I61"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_IMPORTS = [
    "openai",
    "anthropic",
    "from transformers import pipeline",
    "AutoModelForCausalLM",
    "text-generation",
    "chat.completions",
    "llm =",
    "generate(",
]


def test_afirmaciones_CL_I61_zero_llm_control_plane():
    src = (ROOT / "traianus" / "app.py").read_text(encoding="utf-8")
    for token in FORBIDDEN_IMPORTS:
        assert token not in src, f"CL-I61 MUST NOT: control plane invokes LLM ({token})"


def test_afirmaciones_CL_I61_only_deterministic_embedding():
    src = (ROOT / "traianus" / "app.py").read_text(encoding="utf-8")
    assert "SentenceTransformer" in src, "CL-I61: provider is deterministic embedding"
    # No probabilistic generation: the code only projects and persists.
    assert "max_new_tokens" not in src
