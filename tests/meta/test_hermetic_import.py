"""
Hermetic import guards (plan-architect P0.1 / P0.2).

Normative (RFC 2119): importing `traianus.app` and `traianus.bootstrap`
MUST NOT build the SentenceTransformer encoder (L1) and MUST NOT open or
create any database file at import time. The relational schema is created
lazily by the FastAPI lifespan at server boot; the encoder is created
lazily on the first `get_model()` call.

Normative: docs/development/tests/SPEC-global.md
Coverage: HERMETIC-IMPORT
"""
import asyncio
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import traianus.app as main

ROOT = Path(__file__).resolve().parents[2]

SHIM_SOURCE = (
    "class SentenceTransformer:\n"
    "    def __init__(self, *args, **kwargs):\n"
    "        raise RuntimeError(\n"
    '            "SentenceTransformer constructed at import time: import is NOT hermetic"\n'
    "        )\n"
)

PROBE_SCRIPT = (
    "import os\n"
    "import sys\n"
    "import tempfile\n"
    "\n"
    "shim_dir = tempfile.mkdtemp(prefix='st_shim_')\n"
    "shim = os.path.join(shim_dir, 'sentence_transformers.py')\n"
    "with open(shim, 'w', encoding='utf-8') as fh:\n"
    "    fh.write(SHIM_SOURCE)\n"
    "sys.path.insert(0, shim_dir)\n"
    "\n"
    "import traianus.app as app\n"
    "import traianus.bootstrap as bootstrap\n"
    "\n"
    "assert app._model is None, 'app._model must be None after import (lazy init)'\n"
    "assert bootstrap._model is None, 'bootstrap._model must be None after import (lazy init)'\n"
    "assert not os.path.exists('traianus.db'), 'import must not create traianus.db'\n"
    "assert not os.path.exists('traianus.db-wal'), 'import must not create traianus.db-wal'\n"
    "assert not os.path.exists('traianus.db-shm'), 'import must not create traianus.db-shm'\n"
    "print('HERMETIC-IMPORT-OK')\n"
)

EXPECTED_TABLES = {"ingestion_queue", "manifold_nodes", "manifold_edges"}


def _probe_cwd():
    return tempfile.TemporaryDirectory(prefix="probe_cwd_")


def test_import_has_no_model_or_db_side_effects():
    """Importing traianus.app / traianus.bootstrap is side-effect free.

    Runs a subprocess from a pristine temp cwd with an exploding encoder
    shim; asserts no model build, no DB files. This is a real boundary
    probe: the autouse `isolate_db` fixture only patches the parent process,
    so the subprocess sees the true import behavior.
    """
    probe_source = PROBE_SCRIPT.replace("SHIM_SOURCE", repr(SHIM_SOURCE))
    with _probe_cwd() as probe_cwd:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT)
        env["HF_HUB_OFFLINE"] = "1"
        result = subprocess.run(
            [sys.executable, "-c", probe_source],
            cwd=probe_cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    assert result.returncode == 0, f"probe failed:\n{result.stdout}\n{result.stderr}"
    assert "HERMETIC-IMPORT-OK" in result.stdout


def test_server_boot_creates_schema_lazily(monkeypatch, tmp_path):
    """The FastAPI lifespan (server boot) creates the relational schema.

    The schema must not exist at import time; it is materialized on the
    configured DB_PATH when the server starts.
    """
    lazy_db = str(tmp_path / "lazy_schema.db")
    monkeypatch.setattr(main, "DB_PATH", lazy_db)
    assert not os.path.exists(lazy_db), "DB must not exist before boot"

    async def boot():
        async with main.lifespan(main.app):
            pass

    asyncio.run(boot())

    assert os.path.exists(lazy_db), "lifespan must create the DB on the configured path"
    with sqlite3.connect(lazy_db) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert EXPECTED_TABLES <= tables, f"missing tables: {EXPECTED_TABLES - tables}"
