from __future__ import annotations

import base64

from app.models.document import MedicalDocument


def to_fhir_binary(document: MedicalDocument, file_bytes: bytes) -> dict:
    """Serialize authorized private bytes as an HL7 FHIR R4 Binary resource."""
    return {
        "resourceType": "Binary",
        "id": str(document.id),
        "contentType": document.mime_type or "application/octet-stream",
        "securityContext": {
            "reference": f"DocumentReference/{document.id}",
        },
        "data": base64.b64encode(file_bytes).decode("ascii"),
    }
