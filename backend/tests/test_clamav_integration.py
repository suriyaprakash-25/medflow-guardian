import os

import pytest

from app.services.malware import ClamAVScanner, SCAN_CLEAN, SCAN_MALICIOUS


pytestmark = pytest.mark.skipif(
    os.getenv("CLAMAV_INTEGRATION") != "1",
    reason="requires a live clamd service",
)


def _scanner() -> ClamAVScanner:
    return ClamAVScanner(
        host=os.getenv("CLAMAV_HOST", "127.0.0.1"),
        port=int(os.getenv("CLAMAV_PORT", "3310")),
        timeout_seconds=10,
    )


def test_live_clamav_accepts_clean_payload():
    result = _scanner().scan_bytes(b"MedFlow Guardian clean integration payload\n")
    assert result.status == SCAN_CLEAN


def test_live_clamav_detects_eicar_test_signature():
    # EICAR is the industry-standard inert antivirus test signature, not malware.
    eicar = (
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!"
        b"$H+H*"
    )
    result = _scanner().scan_bytes(eicar)
    assert result.status == SCAN_MALICIOUS
