"""Privacy-preserving in-process operational telemetry.

The service exports the Prometheus text format without patient identifiers,
query strings, request bodies, tokens, or raw resource IDs. Render captures the
matching structured log stream from stdout; Prometheus-compatible collectors
can scrape the protected internal endpoint.
"""

from __future__ import annotations

import math
import threading
from collections import defaultdict
from time import perf_counter


_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_lock = threading.Lock()
_http_requests: dict[tuple[str, str, str], int] = defaultdict(int)
_http_duration_count: dict[tuple[str, str], int] = defaultdict(int)
_http_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
_http_duration_buckets: dict[tuple[str, str, float], int] = defaultdict(int)
_authorization: dict[tuple[str, str, str, str], int] = defaultdict(int)
_readiness: int = 0


def monotonic_time() -> float:
    return perf_counter()


def observe_http_request(
    *, method: str, route: str, status_code: int, duration_seconds: float
) -> None:
    method_label = method.upper()
    route_label = route if route.startswith("/") else "unmatched"
    status_label = str(status_code)
    duration = max(0.0, float(duration_seconds))

    with _lock:
        _http_requests[(method_label, route_label, status_label)] += 1
        key = (method_label, route_label)
        _http_duration_count[key] += 1
        _http_duration_sum[key] += duration
        for boundary in _LATENCY_BUCKETS:
            if duration <= boundary:
                _http_duration_buckets[(method_label, route_label, boundary)] += 1


def observe_authorization(
    *, resource_type: str, operation: str, allowed: bool, reason: str | None
) -> None:
    decision = "allow" if allowed else "deny"
    reason_label = "none" if allowed or not reason else reason
    with _lock:
        _authorization[(resource_type, operation, decision, reason_label)] += 1


def set_readiness(ready: bool) -> None:
    global _readiness
    with _lock:
        _readiness = 1 if ready else 0


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(**values: str) -> str:
    return "{" + ",".join(f'{key}="{_escape(value)}"' for key, value in values.items()) + "}"


def render_prometheus() -> str:
    """Return a stable snapshot in Prometheus 0.0.4 exposition format."""
    with _lock:
        requests = dict(_http_requests)
        duration_count = dict(_http_duration_count)
        duration_sum = dict(_http_duration_sum)
        duration_buckets = dict(_http_duration_buckets)
        authorizations = dict(_authorization)
        readiness = _readiness

    lines = [
        "# HELP medflow_up Whether the web process is running.",
        "# TYPE medflow_up gauge",
        "medflow_up 1",
        "# HELP medflow_ready Whether the most recent readiness probe succeeded.",
        "# TYPE medflow_ready gauge",
        f"medflow_ready {readiness}",
        "# HELP medflow_http_requests_total HTTP requests by route template and status.",
        "# TYPE medflow_http_requests_total counter",
    ]
    for (method, route, status), value in sorted(requests.items()):
        lines.append(
            "medflow_http_requests_total"
            + _labels(method=method, route=route, status=status)
            + f" {value}"
        )

    lines.extend(
        [
            "# HELP medflow_http_request_duration_seconds HTTP request latency.",
            "# TYPE medflow_http_request_duration_seconds histogram",
        ]
    )
    for method, route in sorted(duration_count):
        for boundary in _LATENCY_BUCKETS:
            value = duration_buckets.get((method, route, boundary), 0)
            lines.append(
                "medflow_http_request_duration_seconds_bucket"
                + _labels(method=method, route=route, le=str(boundary))
                + f" {value}"
            )
        count = duration_count[(method, route)]
        lines.append(
            "medflow_http_request_duration_seconds_bucket"
            + _labels(method=method, route=route, le="+Inf")
            + f" {count}"
        )
        lines.append(
            "medflow_http_request_duration_seconds_sum"
            + _labels(method=method, route=route)
            + f" {duration_sum[(method, route)]:.9f}"
        )
        lines.append(
            "medflow_http_request_duration_seconds_count"
            + _labels(method=method, route=route)
            + f" {count}"
        )

    lines.extend(
        [
            "# HELP medflow_authorization_decisions_total Central authorization decisions.",
            "# TYPE medflow_authorization_decisions_total counter",
        ]
    )
    for (resource, operation, decision, reason), value in sorted(authorizations.items()):
        lines.append(
            "medflow_authorization_decisions_total"
            + _labels(
                resource=resource,
                operation=operation,
                decision=decision,
                reason=reason,
            )
            + f" {value}"
        )

    # Prometheus requires a trailing newline. Reject accidental non-finite data.
    if any(" nan" in line.lower() or f" {math.inf}" in line.lower() for line in lines):
        raise RuntimeError("Non-finite telemetry value")
    return "\n".join(lines) + "\n"
