from fastapi.testclient import TestClient

from app.main import app
from app.services.interoperability.capability import build_capability_statement


client = TestClient(app)


def test_capability_statement_is_public_r4_and_does_not_overclaim_crud():
    response = client.get("/api/interoperability/metadata")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/fhir+json")
    payload = response.json()
    assert payload["resourceType"] == "CapabilityStatement"
    assert payload["fhirVersion"] == "4.0.1"
    assert payload["kind"] == "instance"
    assert payload["rest"][0]["mode"] == "server"

    resources = {item["type"]: item for item in payload["rest"][0]["resource"]}
    assert set(resources) == {
        "Bundle",
        "Patient",
        "Practitioner",
        "Organization",
        "Consent",
        "MedicationRequest",
        "Observation",
        "DocumentReference",
        "Binary",
    }

    # The general export resources are representation declarations rather than a
    # claim of standalone CRUD support. Binary is the one explicitly implemented
    # FHIR resource read endpoint and must remain read-only.
    assert all(
        "interaction" not in item
        for resource_type, item in resources.items()
        if resource_type != "Binary"
    )
    assert resources["Binary"]["interaction"] == [{"code": "read"}]


def test_capability_builder_uses_runtime_base_url():
    payload = build_capability_statement("https://api.example.test/")
    assert payload["url"] == "https://api.example.test/api/interoperability/metadata"
    assert payload["implementation"]["url"] == "https://api.example.test/api/interoperability"
