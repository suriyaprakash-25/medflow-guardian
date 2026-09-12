"""Fail-closed FHIR R4 Consent mapping and persistence.

FHIR describes policy. Authorization remains the responsibility of MedFlow's
central authorization engine and existing ConsentService.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User


FHIR_STATUS_MAP = {
    "draft": ConsentStatus.DRAFT.value,
    "proposed": ConsentStatus.DRAFT.value,
    "active": ConsentStatus.ACTIVE.value,
    "rejected": ConsentStatus.CANCELLED.value,
    "inactive": ConsentStatus.REVOKED.value,
    "entered-in-error": ConsentStatus.CANCELLED.value,
}
FHIR_ACTION_MAP = {
    "access": {"read"},
    "collect": {"create"},
    "use": {"read"},
    "disclose": {"read", "download"},
    "correct": {"read", "update"},
}
FHIR_PURPOSE_MAP = {
    "TREAT": "TREATMENT",
    "HPAYMT": "BILLING",
    "HOPERAT": "HEALTHCARE_OPERATIONS",
    "RESCH": "RESEARCH",
    "PATRQT": "PATIENT_REQUEST",
    "PUBHLTH": "PUBLIC_HEALTH",
}
FHIR_ACTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentaction"
FHIR_PURPOSE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActReason"
REFERENCE_PATTERN = re.compile(
    r"^(?:https?://[^\s]+/)?(Patient|Practitioner|Organization)/(\d+)$"
)
FHIR_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")


class FHIRConsentError(ValueError):
    """The resource cannot be mapped without weakening policy semantics."""


@dataclass(frozen=True)
class MappedFHIRConsent:
    source_resource_id: str
    patient_id: int
    doctor_id: int | None
    hospital_id: int | None
    status: str
    policy_payload: dict[str, Any]


@dataclass(frozen=True)
class FHIRConsentImportResult:
    consent: Consent
    policy: ConsentPolicyVersion
    state: ConsentState
    created: bool


def _require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FHIRConsentError(f"{field} must be an object")
    return value


def _codes(items: Any, field: str, expected_system: str) -> list[str]:
    if not isinstance(items, list) or not items:
        raise FHIRConsentError(f"{field} must contain at least one coding")
    result: list[str] = []
    for index, item in enumerate(items):
        container = _require_dict(item, f"{field}[{index}]")
        codings = container.get("coding", [container])
        if not isinstance(codings, list) or not codings:
            raise FHIRConsentError(f"{field}[{index}].coding must not be empty")
        for coding_index, coding in enumerate(codings):
            coding = _require_dict(coding, f"{field}[{index}].coding[{coding_index}]")
            if coding.get("system") != expected_system or not isinstance(coding.get("code"), str):
                raise FHIRConsentError(
                    f"{field} contains an unsupported or missing coding system/code"
                )
            result.append(coding["code"])
    return result


def _parse_reference(value: Any, expected_type: str, field: str) -> int:
    reference = _require_dict(value, field).get("reference")
    match = REFERENCE_PATTERN.fullmatch(reference) if isinstance(reference, str) else None
    if not match or match.group(1) != expected_type:
        raise FHIRConsentError(f"{field}.reference must identify a numeric {expected_type}")
    return int(match.group(2))


def _parse_datetime(value: Any, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FHIRConsentError(f"{field} must be an ISO-8601 dateTime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FHIRConsentError(f"{field} must be an ISO-8601 dateTime") from exc
    if parsed.tzinfo is None:
        raise FHIRConsentError(f"{field} must include a timezone")
    return parsed


def _normalize_source_system(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 255:
        raise FHIRConsentError("source_system must be an absolute HTTP(S) base URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise FHIRConsentError("source_system must be an absolute HTTP(S) base URL without credentials, query, or fragment")
    return value.rstrip("/")


def _validate_codeable_concept(value: Any, field: str) -> None:
    concept = _require_dict(value, field)
    codings = concept.get("coding")
    if not isinstance(codings, list) or not codings:
        raise FHIRConsentError(f"{field}.coding must not be empty")
    for index, coding in enumerate(codings):
        coding = _require_dict(coding, f"{field}.coding[{index}]")
        if not isinstance(coding.get("system"), str) or not isinstance(coding.get("code"), str):
            raise FHIRConsentError(f"{field}.coding[{index}] requires system and code")


def map_fhir_consent(resource: dict[str, Any], source_system: str) -> MappedFHIRConsent:
    """Map the explicitly supported subset of an R4 Consent."""
    resource = _require_dict(resource, "Consent")
    if resource.get("resourceType") != "Consent":
        raise FHIRConsentError("resourceType must be Consent")

    resource_id = resource.get("id")
    if not isinstance(resource_id, str) or not FHIR_ID_PATTERN.fullmatch(resource_id):
        raise FHIRConsentError("Consent.id is required for import provenance")
    normalized_source = _normalize_source_system(source_system)

    fhir_status = resource.get("status")
    if fhir_status not in FHIR_STATUS_MAP:
        raise FHIRConsentError(f"Unsupported Consent.status: {fhir_status!r}")
    if not resource.get("policy") and not resource.get("policyRule"):
        raise FHIRConsentError("FHIR R4 requires Consent.policy or Consent.policyRule")
    _validate_codeable_concept(resource.get("scope"), "Consent.scope")
    categories = resource.get("category")
    if not isinstance(categories, list) or not categories:
        raise FHIRConsentError("Consent.category must contain at least one CodeableConcept")
    for index, category in enumerate(categories):
        _validate_codeable_concept(category, f"Consent.category[{index}]")

    patient_id = _parse_reference(resource.get("patient"), "Patient", "Consent.patient")
    provision = _require_dict(resource.get("provision"), "Consent.provision")
    if provision.get("type", "permit") != "permit":
        raise FHIRConsentError("Deny provisions are not supported; import rejected fail-closed")
    if provision.get("provision"):
        raise FHIRConsentError("Nested provisions are not supported; import rejected fail-closed")

    action_codes = _codes(provision.get("action"), "Consent.provision.action", FHIR_ACTION_SYSTEM)
    unknown_actions = sorted(set(action_codes) - FHIR_ACTION_MAP.keys())
    if unknown_actions:
        raise FHIRConsentError(f"Unsupported consent action code(s): {', '.join(unknown_actions)}")
    allowed_operations = sorted({op for code in action_codes for op in FHIR_ACTION_MAP[code]})

    purpose_codes = _codes(provision.get("purpose"), "Consent.provision.purpose", FHIR_PURPOSE_SYSTEM)
    unknown_purposes = sorted(set(purpose_codes) - FHIR_PURPOSE_MAP.keys())
    if unknown_purposes:
        raise FHIRConsentError(f"Unsupported purpose code(s): {', '.join(unknown_purposes)}")
    allowed_purposes = sorted({FHIR_PURPOSE_MAP[code] for code in purpose_codes})

    doctor_ids: set[int] = set()
    hospital_ids: set[int] = set()
    actors = provision.get("actor", [])
    if not isinstance(actors, list):
        raise FHIRConsentError("Consent.provision.actor must be an array")
    for index, actor in enumerate(actors):
        actor = _require_dict(actor, f"Consent.provision.actor[{index}]")
        if not actor.get("role"):
            raise FHIRConsentError(f"Consent.provision.actor[{index}].role is required")
        reference = _require_dict(actor.get("reference"), f"Consent.provision.actor[{index}].reference")
        raw_reference = reference.get("reference")
        match = REFERENCE_PATTERN.fullmatch(raw_reference) if isinstance(raw_reference, str) else None
        if not match or match.group(1) not in {"Practitioner", "Organization"}:
            raise FHIRConsentError(
                "Consent.provision.actor references must identify numeric Practitioner or Organization resources"
            )
        target = int(match.group(2))
        (doctor_ids if match.group(1) == "Practitioner" else hospital_ids).add(target)
    if len(doctor_ids) > 1 or len(hospital_ids) > 1:
        raise FHIRConsentError("A MedFlow consent may scope at most one practitioner and one organization")

    period = _require_dict(provision.get("period") or {}, "Consent.provision.period")
    period_start = _parse_datetime(period.get("start"), "Consent.provision.period.start")
    period_end = _parse_datetime(period.get("end"), "Consent.provision.period.end")
    if period_start and period_end and period_start > period_end:
        raise FHIRConsentError("Consent.provision.period.start must not be after end")

    mapped_status = FHIR_STATUS_MAP[fhir_status]
    now = datetime.now(timezone.utc)
    if mapped_status == ConsentStatus.ACTIVE.value:
        if period_start and period_start > now:
            mapped_status = ConsentStatus.DRAFT.value
        elif period_end and period_end <= now:
            mapped_status = ConsentStatus.EXPIRED.value

    meta = _require_dict(resource.get("meta") or {}, "Consent.meta")
    policy_payload = {
        "allowed_purposes": allowed_purposes,
        "allowed_operations": allowed_operations,
        "fhir": {
            "release": "R4",
            "source_system": normalized_source,
            "resource_id": resource_id.strip(),
            "version_id": meta.get("versionId"),
            "last_updated": meta.get("lastUpdated"),
            "status": fhir_status,
            "period": {"start": period.get("start"), "end": period.get("end")},
        },
    }
    return MappedFHIRConsent(
        source_resource_id=resource_id.strip(),
        patient_id=patient_id,
        doctor_id=next(iter(doctor_ids), None),
        hospital_id=next(iter(hospital_ids), None),
        status=mapped_status,
        policy_payload=policy_payload,
    )


class FHIRConsentImporter:
    def __init__(self, db: Session):
        self._db = db

    def import_consent(
        self, resource: dict[str, Any], source_system: str, actor: User
    ) -> FHIRConsentImportResult:
        mapped = map_fhir_consent(resource, source_system)
        normalized_source = _normalize_source_system(source_system)
        if actor.role != "patient" or actor.id != mapped.patient_id:
            raise FHIRConsentError("The authenticated patient does not match Consent.patient")

        patient = self._db.query(User).filter(
            User.id == mapped.patient_id, User.role == "patient", User.is_active.is_(True)
        ).first()
        if not patient:
            raise FHIRConsentError("Referenced patient does not exist or is inactive")

        if mapped.doctor_id is not None:
            doctor = self._db.query(User).filter(
                User.id == mapped.doctor_id, User.role == "doctor", User.is_active.is_(True)
            ).first()
            if not doctor:
                raise FHIRConsentError("Referenced practitioner does not exist or is inactive")
        if mapped.hospital_id is not None:
            hospital = self._db.query(Hospital).filter(
                Hospital.id == mapped.hospital_id, Hospital.is_active.is_(True)
            ).first()
            if not hospital:
                raise FHIRConsentError("Referenced organization does not exist or is inactive")
        if mapped.doctor_id is not None and mapped.hospital_id is not None:
            membership = self._db.query(HospitalStaff).filter(
                HospitalStaff.user_id == mapped.doctor_id,
                HospitalStaff.hospital_id == mapped.hospital_id,
                HospitalStaff.is_active.is_(True),
            ).first()
            if not membership:
                raise FHIRConsentError("Referenced practitioner is not active in the referenced organization")

        # A row lock cannot protect the first import because no row exists yet.
        # Serialize the short lookup/version-write transaction by external ID.
        if self._db.get_bind().dialect.name == "postgresql":
            lock_key = f"fhir-consent:{normalized_source}:{mapped.source_resource_id}"
            self._db.execute(select(func.pg_advisory_xact_lock(func.hashtext(lock_key))))

        consent = self._db.query(Consent).filter(
            Consent.source_system == normalized_source,
            Consent.source_resource_id == mapped.source_resource_id,
        ).with_for_update().first()
        created = consent is None
        if consent is None:
            consent = Consent(
                patient_id=mapped.patient_id,
                doctor_id=mapped.doctor_id,
                hospital_id=mapped.hospital_id,
                status=mapped.status,
                source_system=normalized_source,
                source_resource_id=mapped.source_resource_id,
            )
            self._db.add(consent)
            self._db.flush()
            next_version = 1
            previous_policy = None
        else:
            if consent.patient_id != mapped.patient_id:
                raise FHIRConsentError("Imported resource identity is already bound to another patient")
            previous_policy = self._db.query(ConsentPolicyVersion).filter(
                ConsentPolicyVersion.consent_id == consent.id,
                ConsentPolicyVersion.status == "active",
            ).order_by(ConsentPolicyVersion.version_number.desc()).first()
            previous_state = self._db.query(ConsentState).filter(
                ConsentState.consent_id == consent.id,
            ).order_by(ConsentState.created_at.desc(), ConsentState.id.desc()).first()
            if (
                previous_policy and previous_state
                and previous_policy.policy_payload == mapped.policy_payload
                and previous_state.status == mapped.status
            ):
                return FHIRConsentImportResult(consent, previous_policy, previous_state, False)
            latest_version = self._db.query(ConsentPolicyVersion.version_number).filter(
                ConsentPolicyVersion.consent_id == consent.id
            ).order_by(ConsentPolicyVersion.version_number.desc()).scalar()
            next_version = (latest_version or 0) + 1
            if previous_policy:
                previous_policy.status = "superseded"
            consent.doctor_id = mapped.doctor_id
            consent.hospital_id = mapped.hospital_id
            consent.status = mapped.status

        policy = ConsentPolicyVersion(
            consent_id=consent.id,
            version_number=next_version,
            policy_payload=mapped.policy_payload,
            status="active",
        )
        self._db.add(policy)
        self._db.flush()
        state = ConsentState(
            consent_id=consent.id,
            policy_version_id=policy.id,
            status=mapped.status,
            reason="Imported from external FHIR R4 Consent",
        )
        self._db.add(state)
        self._db.flush()
        return FHIRConsentImportResult(consent, policy, state, created)
