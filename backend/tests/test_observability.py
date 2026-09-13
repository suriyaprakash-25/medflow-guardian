import json
import logging
from io import StringIO

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.logging import JSONFormatter
from app.core.observability import observe_authorization
from app.main import app


client = TestClient(app)


def test_request_correlation_and_protected_prometheus_metrics(monkeypatch):
    monkeypatch.setattr(settings, "OBSERVABILITY_TOKEN", "metrics-test-token")

    health = client.get("/health", headers={"X-Request-ID": "request-12345"})
    assert health.status_code == 200
    assert health.headers["x-request-id"] == "request-12345"

    assert client.get("/internal/metrics").status_code == 404
    assert (
        client.get(
            "/internal/metrics", headers={"Authorization": "Bearer wrong-token"}
        ).status_code
        == 404
    )

    metrics = client.get(
        "/internal/metrics",
        headers={"Authorization": "Bearer metrics-test-token"},
    )
    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    assert 'medflow_http_requests_total{method="GET",route="/health",status="200"}' in metrics.text
    assert "request-12345" not in metrics.text


def test_invalid_request_id_is_not_reflected():
    response = client.get("/health", headers={"X-Request-ID": "bad id\r\nvalue"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad id\r\nvalue"
    assert len(response.headers["x-request-id"]) == 36


def test_authorization_metric_has_bounded_non_phi_labels(monkeypatch):
    monkeypatch.setattr(settings, "OBSERVABILITY_TOKEN", "metrics-test-token")
    observe_authorization(
        resource_type="document",
        operation="read",
        allowed=False,
        reason="consent_required",
    )
    metrics = client.get(
        "/internal/metrics",
        headers={"Authorization": "Bearer metrics-test-token"},
    ).text
    assert (
        'medflow_authorization_decisions_total{resource="document",operation="read",decision="deny",reason="consent_required"}'
        in metrics
    )


def test_json_logs_redact_nested_secrets_and_avoid_request_payloads():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger = logging.getLogger("medflow-observability-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info(
        "security event",
        extra={
            "event": "authorization_denied",
            "request_id": "request-12345",
            "metadata": {"token": "sensitive", "resource": "document"},
        },
    )
    payload = json.loads(stream.getvalue())
    assert payload["event"] == "authorization_denied"
    assert payload["metadata"]["token"] == "***REDACTED***"
    assert payload["metadata"]["resource"] == "document"
    assert "sensitive" not in stream.getvalue()
