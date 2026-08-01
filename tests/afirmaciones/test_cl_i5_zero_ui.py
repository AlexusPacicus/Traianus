"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-I5 (I-5): the control plane does not embed a user interface
(zero-UI). README declares it in "Not a User Application or UI Framework".
Normative: docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-I5"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_afirmaciones_CL_I5_zero_ui_control_plane():
    src = (ROOT / "traianus" / "app.py").read_text(encoding="utf-8")
    # Control plane exposes only JSON API: must not contain embedded HTML/UI.
    for token in ["<html", "<body", "text/html", "HTMLResponse", "jinja2", "render_template"]:
        assert token not in src, f"CL-I5 MUST NOT: control plane embeds UI ({token})"


def test_afirmaciones_CL_I5_zero_ui_no_static():
    assert not (ROOT / "traianus" / "static").exists(), "CL-I5 MUST NOT: no UI static files"
    assert not (ROOT / "traianus" / "templates").exists(), "CL-I5 MUST NOT: no UI templates"
