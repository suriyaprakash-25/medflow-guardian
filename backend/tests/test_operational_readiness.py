from unittest.mock import Mock

from app.core import operational_readiness


def test_private_storage_readiness_requires_existing_private_bucket(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"id": "medical-documents", "public": False}
    monkeypatch.setattr(operational_readiness.httpx, "get", Mock(return_value=response))
    monkeypatch.setattr(
        operational_readiness.settings, "SUPABASE_BUCKET", "medical-documents"
    )
    assert operational_readiness.private_storage_ready() is True

    response.json.return_value = {"id": "medical-documents", "public": True}
    assert operational_readiness.private_storage_ready() is False


def test_production_dependency_status_fails_closed(monkeypatch):
    monkeypatch.setattr(operational_readiness, "database_ready", lambda: True)
    monkeypatch.setattr(operational_readiness, "clamav_ready", lambda: False)
    monkeypatch.setattr(operational_readiness, "private_storage_ready", lambda: True)
    assert operational_readiness.production_dependency_status() == {
        "database": True,
        "clamav": False,
        "private_storage": True,
    }


def test_clamav_readiness_uses_ping_protocol(monkeypatch):
    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    connection.recv.return_value = b"PONG\0"
    create_connection = Mock(return_value=connection)
    monkeypatch.setattr(operational_readiness.socket, "create_connection", create_connection)
    monkeypatch.setattr(
        operational_readiness.settings, "MALWARE_SCANNER_HOST", "clamav.internal"
    )
    monkeypatch.setattr(operational_readiness.settings, "MALWARE_SCANNER_PORT", 3310)

    assert operational_readiness.clamav_ready() is True
    connection.sendall.assert_called_once_with(b"zPING\0")
