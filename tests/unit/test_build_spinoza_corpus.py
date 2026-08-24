"""Syntactic-integrity tests for the corpus sentence segmenter.

Guarantees under test:
1. Losslessness: joining the segmented sentences with single spaces
   reproduces the whitespace-normalized input exactly (no character lost,
   no character invented).
2. Abbreviation/citation debris ('N.B.', 'Pollock.', 'Gloria.') never
   surfaces as a standalone chunk — it stays attached to its carrier
   sentence.
3. Genuine short sentences ('Man thinks.') remain standalone.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"
                       / "experiments" / "tooling"))

from build_spinoza_corpus import split_sentences


def _norm(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.parametrize("text", [
    "By good I mean that which we certainly know to be useful to us.",
    "Man thinks.",
    "Falsity consists in privation. Q.E.D.",
    "The mind affirms of its body a force (existendi vis) greater or less.",
    "Whatsoever increases or diminishes our power of action (III. xi.), helpeth or hindereth (II. xxvii.).",
])
def test_split_is_lossless(text):
    sentences = split_sentences(text)
    assert _norm(" ".join(sentences)) == _norm(text)


def test_nb_never_standalone():
    text = ("By emotion I mean the modifications of the body, whereby the "
            "active power of the said body is increased or diminished. "
            "N.B. If we can be the adequate cause, I call it an activity.")
    sentences = split_sentences(text)
    assert "N.B." not in sentences
    assert any(s.startswith("N.B.") for s in sentences)


def test_citation_name_never_standalone():
    text = ("I have settled to call such perceptions knowledge from the mere "
            "suggestions of experience. This phrase is Baconian. Pollock.")
    sentences = split_sentences(text)
    assert "Pollock." not in sentences
    assert sentences[-1].endswith("Pollock.")


def test_gloria_never_standalone():
    text = ("This emotion is called glory, and under a contrary condition "
            "shame. Gloria.")
    sentences = split_sentences(text)
    assert "Gloria." not in sentences
    assert sentences[-1].endswith("Gloria.")


def test_short_real_sentence_stays_atomic():
    sentences = split_sentences("Man thinks. Desires follow from nature.")
    assert sentences == ["Man thinks.", "Desires follow from nature."]
