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
    def __init__(self, result, *, fail_commit=False):
        self.result = result
        self.fail_commit = fail_commit
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, *args, **kwargs):
        return _Query(self.result)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("audit unavailable")
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


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


def test_fhir_binary_patient_read_uses_authorization_clean_scan_and_durable_allow_audit(monkeypatch):
    monkeypatch.setattr(
        fhir_binary_api.storage_service,
        "download_document",
        lambda path: b"protected bytes",
    )
    db = _DB(_doc())
    response = fhir_binary_api.read_fhir_binary(
        7,
        purpose=None,
        db=db,
        current_user=SimpleNamespace(id=11, role="patient", is_active=True),
        auth_svc=_Auth(),
    )
    payload = json.loads(response.body)
    assert response.media_type == "application/fhir+json"
    assert payload["resourceType"] == "Binary"
    assert base64.b64decode(payload["data"]) == b"protected bytes"
    assert db.commits == 1
    assert len(db.added) == 1
    assert db.added[0].decision == "ALLOW"
    assert db.added[0].operation == "download_release"
    assert json.loads(db.added[0].metadata_json)["representation"] == "fhir_binary"


def test_fhir_binary_quarantine_fails_closed_without_storage_and_audits_denial(monkeypatch):
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
    db = _DB(_doc(SCAN_PENDING))
    with pytest.raises(HTTPException) as exc:
        fhir_binary_api.read_fhir_binary(
            7,
            purpose=None,
            db=db,
            current_user=SimpleNamespace(id=11, role="patient", is_active=True),
            auth_svc=_Auth(),
        )
    assert exc.value.status_code == 403
    assert "quarantined" in exc.value.detail
    assert called is False
    assert db.commits == 1
    assert len(db.added) == 1
    assert db.added[0].decision == "DENY"
    assert db.added[0].denial_reason == "malware_quarantine"


def test_fhir_binary_release_fails_closed_when_audit_cannot_commit(monkeypatch):
    monkeypatch.setattr(
        fhir_binary_api.storage_service,
        "download_document",
        lambda path: b"protected bytes",
    )
    db = _DB(_doc(), fail_commit=True)
    with pytest.raises(HTTPException) as exc:
        fhir_binary_api.read_fhir_binary(
            7,
            purpose=None,
            db=db,
            current_user=SimpleNamespace(id=11, role="patient", is_active=True),
            auth_svc=_Auth(),
        )
    assert exc.value.status_code == 503
    assert "Security audit" in exc.value.detail
    assert db.rollbacks == 1


def test_capability_statement_claims_only_read_for_binary():
    capability = build_capability_statement("https://api.example.com")
    resources = capability["rest"][0]["resource"]
    binary = next(resource for resource in resources if resource["type"] == "Binary")
    assert binary["interaction"] == [{"code": "read"}]
