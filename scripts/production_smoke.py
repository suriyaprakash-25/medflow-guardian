"""Non-mutating smoke checks for a deployed MedFlow release."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SECURITY_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}


def fetch(url: str, *, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    headers = {"User-Agent": "MedFlow-Production-Smoke/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()


def check_json(url: str, expected: dict[str, str]) -> None:
    status, headers, body = fetch(url)
    if status != 200 or json.loads(body) != expected:
        raise AssertionError(f"{url} failed: HTTP {status}")
    for name, value in SECURITY_HEADERS.items():
        if value.lower() not in headers.get(name, "").lower():
            raise AssertionError(f"{url} missing required {name}")
    if "x-request-id" not in headers:
        raise AssertionError(f"{url} missing X-Request-ID")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--frontend-url", action="append", default=[])
    parser.add_argument("--observability-token")
    args = parser.parse_args()
    api_url = args.api_url.rstrip("/")
    if not api_url.startswith("https://"):
        raise AssertionError("Production API URL must use HTTPS")

    check_json(f"{api_url}/health", {"status": "ok"})
    check_json(f"{api_url}/ready", {"status": "ready"})
    for hidden_path in ("/docs", "/redoc", "/openapi.json", "/internal/metrics"):
        status, _, _ = fetch(f"{api_url}{hidden_path}")
        if status != 404:
            raise AssertionError(f"{hidden_path} must return 404 without credentials")

    if args.observability_token:
        status, _, body = fetch(
            f"{api_url}/internal/metrics", token=args.observability_token
        )
        if status != 200 or b"medflow_up 1" not in body:
            raise AssertionError("Authenticated metrics scrape failed")

    for frontend_url in args.frontend_url:
        if not frontend_url.startswith("https://"):
            raise AssertionError("Production frontend URLs must use HTTPS")
        status, headers, _ = fetch(frontend_url.rstrip("/") + "/")
        if status != 200:
            raise AssertionError(f"Frontend failed: {frontend_url} HTTP {status}")
        for header in ("strict-transport-security", "content-security-policy"):
            if header not in headers:
                raise AssertionError(f"Frontend {frontend_url} missing {header}")

    print("Production smoke validation passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError, URLError) as exc:
        print(f"Production smoke validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
