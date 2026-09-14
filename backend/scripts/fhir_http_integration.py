"""Exercise the running MedFlow API and persist FHIR artifacts for external validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--email", default="patient@demo.com")
    parser.add_argument("--password", default="password")
    parser.add_argument("--output-dir", type=Path, default=Path("build/fhir-http-integration"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(base_url=base_url, timeout=20.0) as client:
        ready = client.get("/ready")
        ready.raise_for_status()

        login = client.post(
            "/api/auth/login",
            data={"username": args.email, "password": args.password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login.raise_for_status()
        access_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        me = client.get("/api/auth/me", headers=headers)
        me.raise_for_status()
        identity = me.json()
        if identity.get("role") != "patient" and identity.get("system_role") != "patient":
            raise RuntimeError("FHIR HTTP integration account is not a patient")
        patient_id = int(identity["id"])

        capability = client.get("/api/interoperability/metadata")
        capability.raise_for_status()
        bundle = client.get(
            f"/api/interoperability/patients/{patient_id}/export",
            params={"purpose": "PATIENT_REQUEST"},
            headers=headers,
        )
        bundle.raise_for_status()

    artifacts = {
        "capability-statement-http.json": capability.json(),
        "patient-export-http.json": bundle.json(),
    }
    for filename, payload in artifacts.items():
        (args.output_dir / filename).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "patient_id": patient_id,
                "artifacts": sorted(artifacts),
                "status": "ok",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
