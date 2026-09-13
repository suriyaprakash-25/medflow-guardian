"""Run the pinned official HL7 validator and fail on FHIR errors."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path


VALIDATOR_VERSION = "6.9.12"
VALIDATOR_SHA256 = "0e53ab1d1a6f1e35f505255c0b8ce10a35fcf27e6e96b503640f784cd07e5ad6"
VALIDATOR_URL = (
    "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/"
    f"{VALIDATOR_VERSION}/validator_cli.jar"
)


def ensure_validator(path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # URL is a constant HTTPS GitHub release and the downloaded bytes are
        # independently checksum-verified below.
        with urllib.request.urlopen(VALIDATOR_URL, timeout=120) as response:  # nosec B310
            path.write_bytes(response.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != VALIDATOR_SHA256:
        raise RuntimeError(f"HL7 validator checksum mismatch: {digest}")


def validate(jar: Path, source: Path, evidence_dir: Path) -> dict[str, int]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = evidence_dir / f"{source.stem}-operation-outcome.json"
    completed = subprocess.run(
        [
            "java",
            "-jar",
            str(jar),
            str(source),
            "-version",
            "4.0.1",
            "-tx",
            "n/a",
            "-output",
            str(output),
        ],
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"HL7 validator process failed for {source}")
    outcome = json.loads(output.read_text(encoding="utf-8-sig"))
    counts = {"fatal": 0, "error": 0, "warning": 0, "information": 0}
    for issue in outcome.get("issue", []):
        severity = issue.get("severity", "error")
        counts[severity] = counts.get(severity, 0) + 1
    if counts["fatal"] or counts["error"]:
        raise RuntimeError(f"FHIR validation errors for {source}: {counts}")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validator-jar",
        type=Path,
        default=Path(tempfile.gettempdir()) / f"validator_cli-{VALIDATOR_VERSION}.jar",
    )
    parser.add_argument(
        "--evidence-dir", type=Path, default=Path("build/fhir-validation")
    )
    parser.add_argument(
        "sources",
        nargs="*",
        type=Path,
        default=list(sorted(Path("tests/fhir_validation").glob("*.json"))),
    )
    args = parser.parse_args()
    ensure_validator(args.validator_jar)
    results = {
        str(source): validate(args.validator_jar, source, args.evidence_dir)
        for source in args.sources
    }
    print(json.dumps({"validator": VALIDATOR_VERSION, "results": results}, indent=2))


if __name__ == "__main__":
    main()
