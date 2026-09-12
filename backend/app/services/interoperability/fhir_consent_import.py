"""Deprecated compatibility shim for the canonical FHIR Consent importer.

R6 intentionally keeps only one semantic mapping/persistence implementation:
``app.services.interoperability.fhir_consent``. This module remains solely so
older internal imports fail in a controlled way rather than silently selecting a
second policy translation path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.user import User
from app.services.interoperability.fhir_consent import (
    FHIRConsentError,
    FHIRConsentImporter,
)


FHIRConsentImportError = FHIRConsentError


@dataclass(frozen=True)
class ImportedConsentResult:
    consent: Consent
    policy_version: ConsentPolicyVersion
    state: ConsentState
    source_resource_id: str
    created: bool


def import_fhir_consent(
    db: Session,
    resource: dict[str, Any],
    *,
    source_system: str,
    actor: User,
) -> ImportedConsentResult:
    """Delegate to the single canonical importer.

    ``source_system`` and ``actor`` are deliberately mandatory. R6 no longer
    fabricates provenance or imports consent outside the authenticated-patient
    authorization boundary.
    """
    result = FHIRConsentImporter(db).import_consent(
        resource=resource,
        source_system=source_system,
        actor=actor,
    )
    return ImportedConsentResult(
        consent=result.consent,
        policy_version=result.policy,
        state=result.state,
        source_resource_id=result.consent.source_resource_id,
        created=result.created,
    )
