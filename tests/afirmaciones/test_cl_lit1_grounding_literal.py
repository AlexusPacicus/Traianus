"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-LIT1 (AGENTS.md §2.4): Topological_Grounding citations exist
character-by-character in the cited source file.

Verifies literal quotes declared in claims_registry.LITERAL_QUOTES.
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-LIT1"""
import pytest

from tests.afirmaciones.claims_registry import LITERAL_QUOTES, resolve


@pytest.mark.parametrize("rel_path,quote", LITERAL_QUOTES)
def test_afirmaciones_CL_LIT1_literal_quote_exists(rel_path, quote):
    content = open(resolve(rel_path), encoding="utf-8").read()
    assert quote in content, (
        f"CL-LIT1 MUST: literal quote not found in {rel_path}: {quote!r}"
    )
