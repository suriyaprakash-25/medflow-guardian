"""Honest FHIR R4 capability declaration for MedFlow's constrained interface."""

from __future__ import annotations


def build_capability_statement(base_url: str) -> dict:
    api_base = base_url.rstrip("/")
    resources = []
    descriptions = {
        "Bundle": "Collection Bundle returned by the authorized patient export operation.",
        "Patient": "Export-only patient representation inside an authorized Bundle.",
        "Practitioner": "Referenced/exported practitioner identity; no standalone CRUD endpoint.",
        "Organization": "Referenced/exported organization identity; no standalone FHIR CRUD endpoint.",
        "Consent": "A fail-closed R4 subset is accepted only at the documented custom import endpoint.",
        "MedicationRequest": "Export-only prescription representation inside a Bundle.",
        "Observation": "Export-only laboratory result representation inside a Bundle.",
        "DocumentReference": "Export-only clinical note or quarantined-document metadata; binary retrieval remains outside FHIR and separately authorized.",
    }
    for resource_type, documentation in descriptions.items():
        resources.append(
            {
                "type": resource_type,
                "profile": f"http://hl7.org/fhir/StructureDefinition/{resource_type}",
                "documentation": documentation,
            }
        )

    return {
        "resourceType": "CapabilityStatement",
        "id": "medflow-guardian-r4",
        "text": {
            "status": "generated",
            "div": (
                '<div xmlns="http://www.w3.org/1999/xhtml">'
                "<p>MedFlow Guardian supports a constrained FHIR R4 export and "
                "Consent-import interface. It is not a general FHIR CRUD server.</p>"
                "</div>"
            ),
        },
        "url": f"{api_base}/api/interoperability/metadata",
        "version": "1.0.0",
        "name": "MedFlowGuardianR4CapabilityStatement",
        "title": "MedFlow Guardian FHIR R4 Capability Statement",
        "status": "active",
        "experimental": False,
        "date": "2026-09-13",
        "publisher": "MedFlow Guardian",
        "description": (
            "FHIR R4 export and Consent-import capabilities implemented by MedFlow. "
            "This is not a general-purpose FHIR CRUD server."
        ),
        "kind": "instance",
        "software": {"name": "MedFlow Guardian API", "version": "0.1.0"},
        "implementation": {
            "description": "MedFlow Guardian secured interoperability API",
            "url": f"{api_base}/api/interoperability",
        },
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "rest": [
            {
                "mode": "server",
                "documentation": (
                    "Capability metadata is public. Patient export requires MedFlow bearer "
                    "authentication and central authorization. Consent import uses the custom "
                    "/fhir/consents/import endpoint. No standard FHIR search, history, update, "
                    "delete, transaction, batch, or Binary endpoint is claimed."
                ),
                "security": {
                    "cors": True,
                    "description": (
                        "MedFlow bearer JWT plus role, organization, relationship, consent, "
                        "purpose, operation, and time checks. CORS uses explicit trusted origins."
                    ),
                },
                "resource": resources,
            }
        ],
    }
