from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User


MEDFLOW_PURPOSE_SYSTEM = "https://medflowguardian.example/fhir/purpose"
FHIR_CONSENT_ACTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentaction"


class FHIRConsentImportError(ValueError):
    """Raised when an inbound FHIR Consent cannot be mapped safely."""


@dataclass(frozen=True)
class ImportedConsentResult:
    consent: Consent
    policy_version: ConsentPolicyVersion
    state: ConsentState
    source_resource_id: Optional[str]


FHIR_STATUS_TO_MEDFLOW = {
    "draft": ConsentStatus.DRAFT.value,
    "proposed": ConsentStatus.DRAFT.value,
    "active": ConsentStatus.ACTIVE.value,
    "rejected": ConsentStatus.CANCELLED.value,
    "inactive": ConsentStatus.REVOKED.value,
    "entered-in-error": ConsentStatus.CANCELLED.value,
}

FHIR_ACTION_TO_MEDFLOW = {
    "access": "read",
    "disclose": "download",
}


def _extract_reference_id(reference: Any, expected_resource: str, field_name: str) -> int:
    if not isinstance(reference, dict):
        raise FHIRConsentImportError(f"{field_name} must be a FHIR Reference object")

    raw_reference = reference.get("reference")
    if not isinstance(raw_reference, str) or not raw_reference.strip():
        raise FHIRConsentImportError(f"{field_name}.reference is required")

    parts = raw_reference.strip().split("/")
    if len(parts) != 2 or parts[0] != expected_resource:
        raise FHIRConsentImportError(
            f"{field_name}.reference must use the form {expected_resource}/<internal-id>"
        )

    try:
        return int(parts[1])
    except (TypeError, ValueError):
        raise FHIRConsentImportError(
            f"{field_name}.reference must contain a numeric MedFlow identifier"
        )


def _extract_single_reference(
    values: Any,
    expected_resource: str,
    field_name: str,
) -> Optional[int]:
    if values is None:
        return None
    if not isinstance(values, list):
        raise FHIRConsentImportError(f"{field_name} must be an array of FHIR Reference objects")
    if len(values) > 1:
        raise FHIRConsentImportError(
            f"{field_name} contains multiple references; MedFlow currently supports one {expected_resource} scope"
        )
    if not values:
        return None
    return _extract_reference_id(values[0], expected_resource, field_name)


def _dedupe(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _map_purposes(provision: Dict[str, Any]) -> List[str]:
    raw_purposes = provision.get("purpose", [])
    if not isinstance(raw_purposes, list):
        raise FHIRConsentImportError("Consent.provision.purpose must be an array")

    purposes: List[str] = []
    for item in raw_purposes:
        if not isinstance(item, dict):
            raise FHIRConsentImportError("Each Consent.provision.purpose entry must be a Coding")
        system = item.get("system")
        code = item.get("code")
        if system != MEDFLOW_PURPOSE_SYSTEM:
            raise FHIRConsentImportError(
                "Unsupported purpose coding system. Import currently accepts only the MedFlow purpose system "
                f"'{MEDFLOW_PURPOSE_SYSTEM}' to avoid ambiguous policy translation."
            )
        if not isinstance(code, str) or not code.strip():
            raise FHIRConsentImportError("Consent.provision.purpose coding.code is required")
        purposes.append(code.strip())

    return _dedupe(purposes)


def _map_operations(provision: Dict[str, Any]) -> List[str]:
    raw_actions = provision.get("action", [])
    if not isinstance(raw_actions, list):
        raise FHIRConsentImportError("Consent.provision.action must be an array")

    operations: List[str] = []
    for action in raw_actions:
        if not isinstance(action, dict):
            raise FHIRConsentImportError("Each Consent.provision.action entry must be a CodeableConcept")
        codings = action.get("coding", [])
        if not isinstance(codings, list) or not codings:
            raise FHIRConsentImportError("Consent.provision.action.coding is required")

        mapped = False
        for coding in codings:
            if not isinstance(coding, dict):
                continue
            if coding.get("system") != FHIR_CONSENT_ACTION_SYSTEM:
                continue
            code = coding.get("code")
            operation = FHIR_ACTION_TO_MEDFLOW.get(code)
            if operation:
                operations.append(operation)
                mapped = True
                break
            raise FHIRConsentImportError(f"Unsupported FHIR consent action code: {code!r}")

        if not mapped:
            raise FHIRConsentImportError(
                f"Consent.provision.action must include a coding from '{FHIR_CONSENT_ACTION_SYSTEM}'"
            )

    return _dedupe(operations)


def _validate_internal_scope(
    db: Session,
    patient_id: int,
    doctor_id: Optional[int],
    hospital_id: Optional[int],
) -> None:
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise FHIRConsentImportError("FHIR Consent references an unknown MedFlow patient")

    if doctor_id is not None:
        doctor = db.query(User).filter(User.id == doctor_id, User.role == "doctor").first()
        if not doctor:
            raise FHIRConsentImportError("FHIR Consent references an unknown MedFlow practitioner")

    if hospital_id is not None:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise FHIRConsentImportError("FHIR Consent references an unknown MedFlow organization")

    if doctor_id is not None and hospital_id is not None:
        membership = db.query(HospitalStaff).filter(
            HospitalStaff.user_id == doctor_id,
            HospitalStaff.hospital_id == hospital_id,
            HospitalStaff.is_active.is_(True),
        ).first()
        if not membership:
            raise FHIRConsentImportError(
                "FHIR Consent practitioner is not an active member of the referenced MedFlow organization"
            )


def import_fhir_consent(db: Session, resource: Dict[str, Any]) -> ImportedConsentResult:
    """Map one FHIR R4 Consent into the existing MedFlow consent model.

    This function only transforms and persists governance data. It does not make
    authorization decisions and deliberately does not introduce a second policy
    engine. All later protected access continues through AuthorizationService and
    ConsentService.
    """
    if not isinstance(resource, dict):
        raise FHIRConsentImportError("FHIR Consent payload must be a JSON object")
    if resource.get("resourceType") != "Consent":
        raise FHIRConsentImportError("resourceType must be 'Consent'")

    fhir_status = resource.get("status")
    medflow_status = FHIR_STATUS_TO_MEDFLOW.get(fhir_status)
    if medflow_status is None:
        raise FHIRConsentImportError(f"Unsupported FHIR Consent.status: {fhir_status!r}")

    patient_id = _extract_reference_id(resource.get("patient"), "Patient", "Consent.patient")
    doctor_id = _extract_single_reference(resource.get("performer"), "Practitioner", "Consent.performer")
    hospital_id = _extract_single_reference(resource.get("organization"), "Organization", "Consent.organization")

    provision = resource.get("provision")
    if not isinstance(provision, dict):
        raise FHIRConsentImportError("Consent.provision is required")

    allowed_purposes = _map_purposes(provision)
    allowed_operations = _map_operations(provision)

    if medflow_status == ConsentStatus.ACTIVE.value:
        if not allowed_purposes:
            raise FHIRConsentImportError("Active imported consent must contain at least one allowed purpose")
        if not allowed_operations:
            raise FHIRConsentImportError("Active imported consent must contain at least one allowed operation")

    _validate_internal_scope(db, patient_id, doctor_id, hospital_id)

    consent = Consent(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        status=medflow_status,
    )
    db.add(consent)
    db.flush()

    source_resource_id = resource.get("id") if isinstance(resource.get("id"), str) else None
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": allowed_purposes,
            "allowed_operations": allowed_operations,
            "provenance": {
                "source": "FHIR_R4_CONSENT_IMPORT",
                "source_resource_id": source_resource_id,
            },
        },
        status="active",
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=medflow_status,
        reason="Imported from FHIR R4 Consent",
    )
    db.add(state)
    db.flush()

    return ImportedConsentResult(
        consent=consent,
        policy_version=policy,
        state=state,
        source_resource_id=source_resource_id,
    )
