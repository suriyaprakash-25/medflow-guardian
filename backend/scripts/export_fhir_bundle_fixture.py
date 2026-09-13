"""Generate an export Bundle fixture through the production serializers."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.clinical import LabResult, Medication, Prescription
from app.models.hospital import Hospital
from app.models.user import User
from app.services.interoperability.fhir_serializers import (
    to_fhir_bundle,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_organization,
    to_fhir_patient,
    to_fhir_practitioner,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/fhir_validation/patient-export-bundle.json"),
    )
    args = parser.parse_args()
    patient = User(id=101, email="patient@example.test", full_name="Example Patient", role="patient", is_active=True)
    practitioner = User(id=202, email="doctor@example.test", full_name="Example Doctor", role="doctor", is_active=True)
    organization = Hospital(id=303, name="Example Hospital", is_active=True)
    medication = Medication(id=404, name="Example Medication")
    prescription = Prescription(
        id=501,
        patient_id=patient.id,
        doctor_id=practitioner.id,
        hospital_id=organization.id,
        medication_id=medication.id,
        medication=medication,
        dosage="One tablet",
        frequency="Daily",
        start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    observation = LabResult(
        id=502,
        patient_id=patient.id,
        doctor_id=practitioner.id,
        hospital_id=organization.id,
        test_name="Example laboratory test",
        result_value="Normal",
        status="completed",
        test_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    bundle = to_fhir_bundle(
        [
            to_fhir_patient(patient),
            to_fhir_practitioner(practitioner),
            to_fhir_organization(organization),
            to_fhir_medication_request(prescription),
            to_fhir_observation(observation),
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
