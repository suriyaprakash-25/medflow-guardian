"""Canonical fail-closed FHIR R4 Consent mapping and persistence.

FHIR Consent is an interoperability representation of policy. It is never an
authorization decision by itself. Protected access remains governed by MedFlow's
Central Authorization Engine and ConsentService.

This module intentionally supports a conservative R4 subset. Any inbound policy
constraint that MedFlow cannot represent and enforce losslessly is rejected rather
than ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re
from typing import Any, Iterable
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User


FHIR_ACTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentaction"
FHIR_PURPOSE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActReason"
FHIR_SCOPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentscope"
FHIR_SCOPE_CODE = "patient-privacy"
FHIR_CATEGORY_SYSTEM = "http://loinc.org"
FHIR_CATEGORY_CODE = "59284-0"
MEDFLOW_POLICY_URI = "https://medflowguardian.example/policies/patient-privacy"
MEDFLOW_ACTOR_ROLE_SYSTEM = "https://medflowguardian.example/fhir/CodeSystem/consent-actor-role"

FHIR_STATUS_TO_MEDFLOW = {
    "draft": ConsentStatus.DRAFT.value,
    "proposed": ConsentStatus.DRAFT.value,
    "active": ConsentStatus.ACTIVE.value,
    "rejected": ConsentStatus.CANCELLED.value,
    "inactive": ConsentStatus.REVOKED.value,
    "entered-in-error": ConsentStatus.CANCELLED.value,
}

# Export is intentionally conservative. Internal states that have no exact R4
# Consent.status equivalent are emitted as a non-authorizing standard status.
MEDFLOW_STATUS_TO_FHIR = {
    ConsentStatus.DRAFT.value: "draft",
    ConsentStatus.ACTIVE.value: "active",
    ConsentStatus.SUSPENDED.value: "inactive",
    ConsentStatus.REVOKED.value: "inactive",
    ConsentStatus.EXPIRED.value: "inactive",
    ConsentStatus.SUPERSEDED.value: "inactive",
    ConsentStatus.CANCELLED.value: "entered-in-error",
}

FHIR_ACTION_TO_MEDFLOW = {
    "access": {"read"},
    "collect": {"create"},
    "use": {"read"},
    "disclose": {"read", "download"},
    "correct": {"read", "update"},
}

FHIR_PURPOSE_TO_MEDFLOW = {
    "TREAT": "TREATMENT",
    "HPAYMT": "BILLING",
    "HOPERAT": "HEALTHCARE_OPERATIONS",
    "RESCH": "RESEARCH",
    "PATRQT": "PATIENT_REQUEST",
    "PUBHLTH": "PUBLIC_HEALTH",
}
MEDFLOW_PURPOSE_TO_FHIR = {value: key for key, value in FHIR_PURPOSE_TO_MEDFLOW.items()}

# Backward-compatible constant names used by earlier tests/imports.
FHIR_STATUS_MAP = FHIR_STATUS_TO_MEDFLOW
FHIR_ACTION_MAP = FHIR_ACTION_TO_MEDFLOW
FHIR_PURPOSE_MAP = FHIR_PURPOSE_TO_MEDFLOW

REFERENCE_PATTERN = re.compile(
    r"^(?:https?://[^\s]+/)?(Patient|Practitioner|Organization)/(\d+)$"
)
FHIR_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")

# These fields materially narrow or alter authorization semantics, but the
# current MedFlow policy model/ConsentService cannot enforce them losslessly.
UNSUPPORTED_PROVISION_FIELDS = {
    "period",
    "securityLabel",
    "class",
    "code",
    "dataPeriod",
    "data",
}


class FHIRConsentError(ValueError):
    """Raised when FHIR Consent semantics cannot be represented safely."""


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


def _normalize_string_values(values: Iterable[Any], field: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise FHIRConsentError(f"{field} values must be non-empty strings")
        item = value.strip()
        if item not in seen:
            seen.add(item)
            normalized.append(item)
    return normalized


def _codes(items: Any, field: str, expected_system: str) -> list[str]:
    if not isinstance(items, list) or not items:
        raise FHIRConsentError(f"{field} must contain at least one coding")
    result: list[str] = []
    for index, item in enumerate(items):
        container = _require_dict(item, f"{field}[{index}]")
        codings = container.get("coding", [container])
        if not isinstance(codings, list) or not codings:
            raise FHIRConsentError(f"{field}[{index}].coding must not be empty")
        matched = False
        for coding_index, coding in enumerate(codings):
            coding = _require_dict(coding, f"{field}[{index}].coding[{coding_index}]")
            system = coding.get("system")
            code = coding.get("code")
            if system == expected_system and isinstance(code, str) and code:
                result.append(code)
                matched = True
            elif system == expected_system:
                raise FHIRConsentError(f"{field} contains a missing coding code")
        if not matched:
            raise FHIRConsentError(
                f"{field} must include a coding from {expected_system!r}"
            )
    return result


def _parse_reference(value: Any, expected_type: str, field: str) -> int:
    reference = _require_dict(value, field).get("reference")
    match = REFERENCE_PATTERN.fullmatch(reference) if isinstance(reference, str) else None
    if not match or match.group(1) != expected_type:
        raise FHIRConsentError(f"{field}.reference must identify a numeric {expected_type}")
    return int(match.group(2))


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
        raise FHIRConsentError(
            "source_system must be an absolute HTTP(S) base URL without credentials, query, or fragment"
        )
    return value.rstrip("/")


def _validate_codeable_concept(value: Any, field: str) -> list[dict[str, Any]]:
    concept = _require_dict(value, field)
    codings = concept.get("coding")
    if not isinstance(codings, list) or not codings:
        raise FHIRConsentError(f"{field}.coding must not be empty")
    result: list[dict[str, Any]] = []
    for index, coding in enumerate(codings):
        coding = _require_dict(coding, f"{field}.coding[{index}]")
        if not isinstance(coding.get("system"), str) or not isinstance(coding.get("code"), str):
            raise FHIRConsentError(f"{field}.coding[{index}] requires system and code")
        result.append(coding)
    return result


def _require_supported_scope_and_category(resource: dict[str, Any]) -> None:
    scope_codings = _validate_codeable_concept(resource.get("scope"), "Consent.scope")
    if not any(
        coding.get("system") == FHIR_SCOPE_SYSTEM and coding.get("code") == FHIR_SCOPE_CODE
        for coding in scope_codings
    ):
        raise FHIRConsentError("Unsupported Consent.scope; only patient-privacy is supported")

    categories = resource.get("category")
    if not isinstance(categories, list) or not categories:
        raise FHIRConsentError("Consent.category must contain at least one CodeableConcept")
    supported = False
    for index, category in enumerate(categories):
        codings = _validate_codeable_concept(category, f"Consent.category[{index}]")
        if any(
            coding.get("system") == FHIR_CATEGORY_SYSTEM and coding.get("code") == FHIR_CATEGORY_CODE
            for coding in codings
        ):
            supported = True
    if not supported:
        raise FHIRConsentError("Unsupported Consent.category for the MedFlow R4 import profile")


def _validate_policy_reference(resource: dict[str, Any]) -> None:
    policy = resource.get("policy")
    policy_rule = resource.get("policyRule")
    if not policy and not policy_rule:
        raise FHIRConsentError("FHIR R4 requires Consent.policy or Consent.policyRule")
    if policy is not None:
        if not isinstance(policy, list) or not policy:
            raise FHIRConsentError("Consent.policy must be a non-empty array")
        for index, item in enumerate(policy):
            item = _require_dict(item, f"Consent.policy[{index}]")
            uri = item.get("uri")
            authority = item.get("authority")
            if not (isinstance(uri, str) and uri.strip()) and not (
                isinstance(authority, str) and authority.strip()
            ):
                raise FHIRConsentError(
                    f"Consent.policy[{index}] must contain uri or authority"
                )
    if policy_rule is not None:
        _validate_codeable_concept(policy_rule, "Consent.policyRule")


def _actor_role_code(role: Any, field: str) -> str:
    role = _require_dict(role, field)
    text = role.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip().lower()
    codings = role.get("coding")
    if not isinstance(codings, list) or not codings:
        raise FHIRConsentError(f"{field} requires text or coding")
    for index, coding in enumerate(codings):
        coding = _require_dict(coding, f"{field}.coding[{index}]")
        if coding.get("system") == MEDFLOW_ACTOR_ROLE_SYSTEM and isinstance(coding.get("code"), str):
            return coding["code"].strip().lower()
    raise FHIRConsentError(f"{field} uses an unsupported actor-role coding")


def medflow_status_to_fhir_status(status: str) -> str:
    mapped = MEDFLOW_STATUS_TO_FHIR.get(status)
    if mapped is None:
        raise FHIRConsentError(f"Unsupported MedFlow consent status for FHIR export: {status!r}")
    return mapped


def medflow_purposes_to_fhir_codes(values: Iterable[Any]) -> list[str]:
    purposes = _normalize_string_values(values, "allowed_purposes")
    if not purposes:
        raise FHIRConsentError("FHIR Consent export requires at least one allowed purpose")
    result: list[str] = []
    for purpose in purposes:
        code = MEDFLOW_PURPOSE_TO_FHIR.get(purpose.upper())
        if code is None:
            raise FHIRConsentError(
                f"MedFlow purpose {purpose!r} cannot be represented by the supported FHIR R4 profile"
            )
        result.append(code)
    return result


def medflow_operations_to_fhir_actions(values: Iterable[Any]) -> list[str]:
    operations = {value.lower() for value in _normalize_string_values(values, "allowed_operations")}
    if not operations:
        raise FHIRConsentError("FHIR Consent export requires at least one allowed operation")

    # Find a deterministic set of FHIR actions whose imported union is exactly
    # the internal operation set. Never choose an action that broadens authority.
    action_codes = sorted(FHIR_ACTION_TO_MEDFLOW)
    for count in range(1, len(action_codes) + 1):
        for candidate in combinations(action_codes, count):
            mapped: set[str] = set()
            for action in candidate:
                mapped.update(FHIR_ACTION_TO_MEDFLOW[action])
            if mapped == operations:
                return list(candidate)
    raise FHIRConsentError(
        "MedFlow allowed_operations cannot be represented losslessly by the supported FHIR consent actions"
    )


def map_fhir_consent(resource: dict[str, Any], source_system: str) -> MappedFHIRConsent:
    """Map the explicitly supported, fail-closed subset of FHIR R4 Consent."""
    resource = _require_dict(resource, "Consent")
    if resource.get("resourceType") != "Consent":
        raise FHIRConsentError("resourceType must be Consent")

    resource_id = resource.get("id")
    if not isinstance(resource_id, str) or not FHIR_ID_PATTERN.fullmatch(resource_id):
        raise FHIRConsentError("Consent.id is required for import provenance")
    normalized_source = _normalize_source_system(source_system)

    fhir_status = resource.get("status")
    if fhir_status not in FHIR_STATUS_TO_MEDFLOW:
        raise FHIRConsentError(f"Unsupported Consent.status: {fhir_status!r}")

    _require_supported_scope_and_category(resource)
    _validate_policy_reference(resource)
    patient_id = _parse_reference(resource.get("patient"), "Patient", "Consent.patient")

    provision = _require_dict(resource.get("provision"), "Consent.provision")
    if provision.get("type", "permit") != "permit":
        raise FHIRConsentError("Deny provisions are not supported; import rejected fail-closed")
    if provision.get("provision"):
        raise FHIRConsentError("Nested provisions are not supported; import rejected fail-closed")
    unsupported = sorted(
        field
        for field in UNSUPPORTED_PROVISION_FIELDS
        if provision.get(field) not in (None, [], {})
    )
    if unsupported:
        raise FHIRConsentError(
            "FHIR Consent contains policy constraints that MedFlow cannot enforce losslessly: "
            + ", ".join(unsupported)
        )

    action_codes = _codes(
        provision.get("action"),
        "Consent.provision.action",
        FHIR_ACTION_SYSTEM,
    )
    unknown_actions = sorted(set(action_codes) - FHIR_ACTION_TO_MEDFLOW.keys())
    if unknown_actions:
        raise FHIRConsentError(
            f"Unsupported consent action code(s): {', '.join(unknown_actions)}"
        )
    allowed_operations = sorted(
        {operation for code in action_codes for operation in FHIR_ACTION_TO_MEDFLOW[code]}
    )

    purpose_codes = _codes(
        provision.get("purpose"),
        "Consent.provision.purpose",
        FHIR_PURPOSE_SYSTEM,
    )
    unknown_purposes = sorted(set(purpose_codes) - FHIR_PURPOSE_TO_MEDFLOW.keys())
    if unknown_purposes:
        raise FHIRConsentError(
            f"Unsupported purpose code(s): {', '.join(unknown_purposes)}"
        )
    allowed_purposes = sorted(
        {FHIR_PURPOSE_TO_MEDFLOW[code] for code in purpose_codes}
    )

    doctor_ids: set[int] = set()
    hospital_ids: set[int] = set()
    actors = provision.get("actor", [])
    if not isinstance(actors, list):
        raise FHIRConsentError("Consent.provision.actor must be an array")
    for index, actor in enumerate(actors):
        actor = _require_dict(actor, f"Consent.provision.actor[{index}]")
        role_code = _actor_role_code(
            actor.get("role"),
            f"Consent.provision.actor[{index}].role",
        )
        reference = _require_dict(
            actor.get("reference"),
            f"Consent.provision.actor[{index}].reference",
        )
        raw_reference = reference.get("reference")
        match = REFERENCE_PATTERN.fullmatch(raw_reference) if isinstance(raw_reference, str) else None
        if not match or match.group(1) not in {"Practitioner", "Organization"}:
            raise FHIRConsentError(
                "Consent.provision.actor references must identify numeric Practitioner or Organization resources"
            )
        resource_type, raw_id = match.groups()
        if resource_type == "Practitioner" and role_code != "recipient":
            raise FHIRConsentError(
                "Practitioner consent actors must use the supported recipient role"
            )
        if resource_type == "Organization" and role_code not in {"custodian", "recipient"}:
            raise FHIRConsentError(
                "Organization consent actors must use the supported custodian or recipient role"
            )
        target = int(raw_id)
        (doctor_ids if resource_type == "Practitioner" else hospital_ids).add(target)

    if len(doctor_ids) > 1 or len(hospital_ids) > 1:
        raise FHIRConsentError(
            "A MedFlow consent may scope at most one practitioner and one organization"
        )

    mapped_status = FHIR_STATUS_TO_MEDFLOW[fhir_status]
    meta = _require_dict(resource.get("meta") or {}, "Consent.meta")
    version_id = meta.get("versionId")
    if version_id is not None and (not isinstance(version_id, str) or len(version_id) > 255):
        raise FHIRConsentError("Consent.meta.versionId must be a string when present")
    last_updated = meta.get("lastUpdated")
    if last_updated is not None and not isinstance(last_updated, str):
        raise FHIRConsentError("Consent.meta.lastUpdated must be a string when present")

    policy_payload = {
        "allowed_purposes": allowed_purposes,
        "allowed_operations": allowed_operations,
        "fhir": {
            "release": "R4",
            "source_system": normalized_source,
            "resource_id": resource_id,
            "version_id": version_id,
            "last_updated": last_updated,
            "status": fhir_status,
        },
    }
    return MappedFHIRConsent(
        source_resource_id=resource_id,
        patient_id=patient_id,
        doctor_id=next(iter(doctor_ids), None),
        hospital_id=next(iter(hospital_ids), None),
        status=mapped_status,
        policy_payload=policy_payload,
    )


class FHIRConsentImporter:
    """Persist canonical FHIR Consent mappings into MedFlow version/state history."""

    def __init__(self, db: Session):
        self._db = db

    def _validate_internal_scope(self, mapped: MappedFHIRConsent) -> None:
        patient = self._db.query(User).filter(
            User.id == mapped.patient_id,
            User.role == "patient",
            User.is_active.is_(True),
        ).first()
        if not patient:
            raise FHIRConsentError("Referenced patient does not exist or is inactive")

        active_authority = mapped.status == ConsentStatus.ACTIVE.value

        if mapped.doctor_id is not None:
            doctor_query = self._db.query(User).filter(
                User.id == mapped.doctor_id,
                User.role == "doctor",
            )
            if active_authority:
                doctor_query = doctor_query.filter(User.is_active.is_(True))
            if not doctor_query.first():
                raise FHIRConsentError(
                    "Referenced practitioner does not exist or is not eligible for active consent"
                )

        if mapped.hospital_id is not None:
            hospital_query = self._db.query(Hospital).filter(Hospital.id == mapped.hospital_id)
            if active_authority:
                hospital_query = hospital_query.filter(Hospital.is_active.is_(True))
            if not hospital_query.first():
                raise FHIRConsentError(
                    "Referenced organization does not exist or is not eligible for active consent"
                )

        if active_authority and mapped.doctor_id is not None and mapped.hospital_id is not None:
            membership = self._db.query(HospitalStaff).filter(
                HospitalStaff.user_id == mapped.doctor_id,
                HospitalStaff.hospital_id == mapped.hospital_id,
                HospitalStaff.is_active.is_(True),
            ).first()
            if not membership:
                raise FHIRConsentError(
                    "Referenced practitioner is not active in the referenced organization"
                )

    def import_consent(
        self,
        resource: dict[str, Any],
        source_system: str,
        actor: User,
    ) -> FHIRConsentImportResult:
        mapped = map_fhir_consent(resource, source_system)
        normalized_source = _normalize_source_system(source_system)
        if actor.role != "patient" or actor.id != mapped.patient_id:
            raise FHIRConsentError(
                "The authenticated patient does not match Consent.patient"
            )

        self._validate_internal_scope(mapped)

        # A row lock cannot protect the first import because no row exists yet.
        # Serialize the short lookup/version-write transaction by external ID.
        if self._db.get_bind().dialect.name == "postgresql":
            lock_key = f"fhir-consent:{normalized_source}:{mapped.source_resource_id}"
            self._db.execute(
                select(func.pg_advisory_xact_lock(func.hashtext(lock_key)))
            )

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
            previous_state = None
        else:
            if consent.patient_id != mapped.patient_id:
                raise FHIRConsentError(
                    "Imported resource identity is already bound to another patient"
                )
            previous_policy = self._db.query(ConsentPolicyVersion).filter(
                ConsentPolicyVersion.consent_id == consent.id,
                ConsentPolicyVersion.status == "active",
            ).order_by(ConsentPolicyVersion.version_number.desc()).first()
            previous_state = self._db.query(ConsentState).filter(
                ConsentState.consent_id == consent.id,
            ).order_by(ConsentState.created_at.desc(), ConsentState.id.desc()).first()

            if previous_policy and previous_state:
                previous_fhir = previous_policy.policy_payload.get("fhir", {})
                incoming_fhir = mapped.policy_payload.get("fhir", {})
                previous_external_version = previous_fhir.get("version_id")
                incoming_external_version = incoming_fhir.get("version_id")
                if (
                    previous_external_version is not None
                    and incoming_external_version == previous_external_version
                    and (
                        previous_policy.policy_payload != mapped.policy_payload
                        or previous_state.status != mapped.status
                    )
                ):
                    raise FHIRConsentError(
                        "Conflicting FHIR Consent content was supplied for an already imported meta.versionId"
                    )

                if (
                    previous_policy.policy_payload == mapped.policy_payload
                    and previous_state.status == mapped.status
                    and consent.doctor_id == mapped.doctor_id
                    and consent.hospital_id == mapped.hospital_id
                ):
                    return FHIRConsentImportResult(
                        consent,
                        previous_policy,
                        previous_state,
                        False,
                    )

            latest_version = self._db.query(
                ConsentPolicyVersion.version_number
            ).filter(
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
