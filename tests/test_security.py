"""
Perímetro Zero-Trust y Validador TridenGuard.
Cubre: Autenticación por token, CORS enumerado, Ingress Allowlist y Compuerta TridenGuard.
"""
import json
import pytest
from traianus.security.validator import validate_proposal

def test_zero_trust_ingress_allowlist(client, auth_headers):
    """Rechaza payloads que no sean text/plain con HTTP 415."""
    res_bad = client.post("/ingesta", json={"type": "application/json", "text": "{}"}, headers=auth_headers)
    assert res_bad.status_code == 415
    
    res_good = client.post("/ingesta", json={"type": "text/plain", "text": "ok"}, headers=auth_headers)
    assert res_good.status_code == 200

def test_protected_routes_require_token(client):
    """Rutas mutantes devuelven 401 si falta el header x-traianus-token."""
    res = client.post("/ingesta", json={"type": "text/plain", "text": "unauthorized"})
    assert res.status_code == 401

def test_tridenguard_validator_gate():
    """Validación Zero-Trust de propuestas (5 Radicales)."""
    valid_prop = json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "x = 1",
        "Topological_Grounding": "auto_calibrate_critical_threshold()",
        "Safety_Abort": "NONE"
    })
    decision = validate_proposal(valid_prop, "traianus/app.py")
    assert decision["status"] == "VALIDATED"
    assert decision["final_decision"] == "EXECUTE_SAFE"
