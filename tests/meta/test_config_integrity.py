"""
Config integrity guardians (OSS Readiness Fase 0).

Normative (RFC 2119): every path declared in `opencode.jsonc` — the
`instructions` list and any path-like argument of each MCP `command` — MUST
point to a file that exists physically in the repository. This guards the
live `tridenguard-validator` MCP integration and the instruction files
against silent breakage when tooling is moved or renamed.

Normative: docs/development/tests/SPEC-template.md
Coverage: CONFIG-INTEGRITY
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "opencode.jsonc"

PATH_SUFFIXES = (".py", ".md", ".json", ".jsonc", ".json5")


def _strip_jsonc(text: str) -> str:
    """Removes // and /* */ comments from a JSONC blob (string-safe)."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            out.append(text[i : j + 1])
            i = j + 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end == -1 else end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


@pytest.fixture(scope="module")
def config():
    if not CONFIG_PATH.exists():
        pytest.skip("opencode.jsonc not present")
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.loads(_strip_jsonc(fh.read()))


def _is_path_like(arg: str) -> bool:
    if arg.startswith(("-", "{")):
        return False
    if arg.endswith(PATH_SUFFIXES):
        return True
    return "/" in arg or arg.startswith(".")


def _resolve(arg: str) -> Path:
    return (ROOT / arg.lstrip("/")).resolve()


def test_config_integrity_instruction_files_exist(config):
    """CONFIG-INTEGRITY: instruction files exist and stay inside the repo."""
    missing = []
    outside = []
    for instr in config.get("instructions", []):
        p = _resolve(instr)
        if not p.exists():
            missing.append(instr)
        elif not p.is_relative_to(ROOT):
            outside.append(instr)
    assert not missing, f"missing instruction files: {missing}"
    assert not outside, f"instruction paths outside repo: {outside}"


def test_config_integrity_mcp_command_paths_exist(config):
    """CONFIG-INTEGRITY: MCP command path-like args point to real files."""
    missing = []
    for name, server in config.get("mcp", {}).items():
        for arg in server.get("command", []):
            if not _is_path_like(arg):
                continue
            if not _resolve(arg).exists():
                missing.append(f"{name}: {arg}")
    assert not missing, f"missing MCP script paths: {missing}"
