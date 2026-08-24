"""
Traianus — Deterministic spatial control plane.

Official Python package of the deterministic spatial substrate Traianus.
Contains:

* ``traianus.app``       — FastAPI control plane (endpoints, pipeline, persistence).
* ``traianus.bootstrap`` — Generation and anchoring of the geodetic basis (NSM primes).

Usage as an installable application::

    pip install -e .
    traianus-bootstrap   # anchors the geodetic basis in SQLite
"""

__version__ = "1.0.1"
