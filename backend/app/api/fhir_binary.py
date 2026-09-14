from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_authorization_service, get_current_user
from app.core.database import get_db
from app.models.document import MedicalDocument
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.consent_context import resolve_active_document_grant
from app.services.interoperability.fhir_binary import to_fhir_binary
from app.services.malware import SCAN_CLEAN, SCAN_ERROR, SCAN_MALICIOUS, SCAN_PENDING
from app.services.storage import storage_service


router = APIRouter()


@router.get("/interoperability/fhir/Binary/{document_id}")
def read_fhir_binary(
    document_id: int,
    purpose: Optional[str] = Query(
        None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    """Read one protected document as a FHIR R4 Binary resource."""
    document = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.id == document_id)
        .first()
    )

    trusted_grant = None
    if current_user.role == "doctor" and document is not None:
        if purpose is None:
            raise HTTPException(
                status_code=403,
                detail="PURPOSE_REQUIRED: practitioner FHIR Binary read requires an explicit purpose",
            )
        trusted_grant = resolve_active_document_grant(
            db,
            doctor_id=current_user.id,
            document=document,
        )

    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_user,
            operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=db,
            resource=document,
            hospital_id=document.hospital_id if document else None,
            patient_id=document.patient_id if document else None,
            purpose=purpose,
            consent_id=(trusted_grant.consent_id if trusted_grant else None),
            relationship_context=trusted_grant,
            enforcement_point="fastapi-fhir-binary-pep",
        )
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=404 if decision.detail == "Document not found" else 403,
            detail=decision.detail,
        )

    if document.scan_status != SCAN_CLEAN:
        if document.scan_status == SCAN_MALICIOUS:
            detail = "FHIR Binary blocked: malware detected"
        elif document.scan_status == SCAN_PENDING:
            detail = "FHIR Binary remains quarantined pending malware scan"
        elif document.scan_status == SCAN_ERROR:
            detail = "FHIR Binary remains quarantined because malware scanning failed"
        else:
            detail = "FHIR Binary remains quarantined because scan state is not releasable"
        raise HTTPException(status_code=403, detail=detail)

    file_bytes = storage_service.download_document(document.stored_filename)
    return JSONResponse(
        to_fhir_binary(document, file_bytes),
        media_type="application/fhir+json",
    )
