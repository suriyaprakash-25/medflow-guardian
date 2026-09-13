"""Write the canonical CapabilityStatement for external validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.interoperability.capability import build_capability_statement


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://api.medflow.example")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/fhir_validation/capability-statement.json"),
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_capability_statement(args.base_url), indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
