"""Single source of truth for the E_n adjacency epsilon (audit N4).

TRAIANUS_EPSILON_EDGE is environment-overridable at server boot; every
consumer (HTTP layer, bridge auditor, experiments) must resolve through
`traianus.core.resolve_epsilon_edge` so an audited adjacency can never
silently diverge from the persisted one.
"""
import inspect
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _unset(var: str):
    old = os.environ.pop(var, None)
    return old


def _restore(var: str, old):
    if old is None:
        os.environ.pop(var, None)
    else:
        os.environ[var] = old


def test_resolver_exists_with_default():
    from traianus.config import DEFAULT_EPSILON_EDGE, resolve_epsilon_edge

    assert DEFAULT_EPSILON_EDGE == 0.8
    old = _unset("TRAIANUS_EPSILON_EDGE")
    try:
        assert resolve_epsilon_edge() == 0.8
    finally:
        _restore("TRAIANUS_EPSILON_EDGE", old)


def test_resolver_honors_env_override():
    from traianus.config import resolve_epsilon_edge

    old = _unset("TRAIANUS_EPSILON_EDGE")
    os.environ["TRAIANUS_EPSILON_EDGE"] = "0.55"
    try:
        assert resolve_epsilon_edge() == 0.55
    finally:
        _restore("TRAIANUS_EPSILON_EDGE", old)


def test_http_layer_resolves_through_core():
    import traianus.app as app_module

    assert "resolve_epsilon_edge" in inspect.getsource(app_module)


def test_bridge_auditor_resolves_through_core():
    import tools.analyze_bridges as bridges

    assert "resolve_epsilon_edge" in inspect.getsource(bridges)
    # The hardcoded local constant must be gone from the tool module.
    tool_src = Path(bridges.__file__).read_text(encoding="utf-8")
    assert "EPSILON = 0.8" not in tool_src
