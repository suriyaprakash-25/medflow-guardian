import base64
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import fhir_binary as fhir_binary_api
from app.services.interoperability.capability import build_capability_statement
from app.services.interoperability.fhir_binary import to_fhir_binary
from app.services.malware import SCAN_CLEAN, SCAN_PENDING


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class _DB:
    def __init__(self, result):
        self.result = result

    def query(self, *args, **kwargs):
        return _Query(self.result)


class _Allow:
    allowed = True
    detail = ""


class _Auth:
    def authorize(self, ctx):
        return _Allow()


def _doc(scan_status=SCAN_CLEAN):
    return SimpleNamespace(
        id=7,
        patient_id=11,
        hospital_id=3,
        uploaded_by_doctor_id=22,
        mime_type="text/plain",
        stored_filename="patient/11/document.txt",
        scan_status=scan_status,
    )


def test_binary_serializer_is_valid_base64_and_never_contains_storage_key():
    resource = to_fhir_binary(_doc(), b"protected bytes")
    assert resource["resourceType"] == "Binary"
    assert resource["contentType"] == "text/plain"
    assert base64.b64decode(resource["data"]) == b"protected bytes"
    assert "patient/11/document.txt" not in json.dumps(resource)


def test_fhir_binary_patient_read_uses_authorization_and_clean_scan(monkeypatch):
    monkeypatch.setattr(
        fhir_binary_api.storage_service,
        "download_document",
        lambda path: b"protected bytes",
    )
    response = fhir_binary_api.read_fhir_binary(
        7,
        purpose=None,
        db=_DB(_doc()),
        current_user=SimpleNamespace(id=11, role="patient", is_active=True),
        auth_svc=_Auth(),
    )
    payload = json.loads(response.body)
    assert response.media_type == "application/fhir+json"
    assert payload["resourceType"] == "Binary"
    assert base64.b64decode(payload["data"]) == b"protected bytes"


def test_fhir_binary_quarantine_fails_closed(monkeypatch):
    called = False

    def should_not_download(path):
        nonlocal called
        called = True
        return b"no"

    monkeypatch.setattr(
        fhir_binary_api.storage_service,
        "download_document",
        should_not_download,
    )
    with pytest.raises(HTTPException) as exc:
        fhir_binary_api.read_fhir_binary(
            7,
            purpose=None,
            db=_DB(_doc(SCAN_PENDING)),
            current_user=SimpleNamespace(id=11, role="patient", is_active=True),
            auth_svc=_Auth(),
        )
    assert exc.value.status_code == 403
    assert "quarantined" in exc.value.detail
    assert called is False


def test_capability_statement_claims_only_read_for_binary():
    capability = build_capability_statement("https://api.example.com")
    resources = capability["rest"][0]["resource"]
    binary = next(resource for resource in resources if resource["type"] == "Binary")
    assert binary["interaction"] == [{"code": "read"}]
