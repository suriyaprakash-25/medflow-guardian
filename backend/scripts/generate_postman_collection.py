"""Generate the canonical assertion-based Postman route contract collection."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.main import app


OUTPUT = (
    Path(__file__).parents[2]
    / "docs"
    / "postman"
    / "MedFlow-All-Endpoints.postman_collection.json"
)
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
PUBLIC_EXPECTATIONS = {
    ("GET", "/health"): 200,
    ("GET", "/ready"): 200,
    ("GET", "/api/interoperability/metadata"): 200,
    ("POST", "/api/auth/login"): 422,
    ("POST", "/api/auth/mfa/verify"): 401,
    ("POST", "/api/auth/refresh"): 401,
    ("POST", "/api/auth/logout"): 200,
    # OIDC entry points must be callable before MedFlow authentication exists.
    # CI intentionally has no external provider configured, so challenge fails
    # closed as an unknown provider while an empty exchange body fails schema
    # validation before any upstream trust decision is attempted.
    ("GET", "/api/auth/oidc/providers"): 200,
    ("POST", "/api/auth/oidc/{provider}/challenge"): 404,
    ("POST", "/api/auth/oidc/{provider}/exchange"): 422,
}


def _postman_path(path: str) -> str:
    return re.sub(r"\{([^}]+)\}", r"{{\1}}", path)


def _test_script(*, expected_status: int, path: str) -> list[str]:
    script = [
        f'pm.test("status is {expected_status}", function () {{',
        f"  pm.response.to.have.status({expected_status});",
        "});",
        'pm.test("security headers are present", function () {',
        '  pm.expect(pm.response.headers.get("X-Content-Type-Options")).to.eql("nosniff");',
        '  pm.expect(pm.response.headers.get("X-Frame-Options")).to.eql("DENY");',
        '  pm.expect(pm.response.headers.get("Cache-Control")).to.eql("no-store");',
        "});",
    ]
    if path in {"/health", "/ready"}:
        expected_value = "ok" if path == "/health" else "ready"
        script.extend(
            [
                'pm.test("health payload is correct", function () {',
                f'  pm.expect(pm.response.json().status).to.eql("{expected_value}");',
                "});",
            ]
        )
    if path == "/api/interoperability/metadata":
        script.extend(
            [
                'pm.test("FHIR capability payload is correct", function () {',
                '  pm.expect(pm.response.headers.get("Content-Type")).to.include("application/fhir+json");',
                '  pm.expect(pm.response.json().resourceType).to.eql("CapabilityStatement");',
                '  pm.expect(pm.response.json().fhirVersion).to.eql("4.0.1");',
                "});",
            ]
        )
    return script


def _request_item(method: str, path: str, tag: str) -> dict:
    expected_status = PUBLIC_EXPECTATIONS.get((method, path), 401)
    accept = (
        "application/fhir+json"
        if path == "/api/interoperability/metadata"
        else "application/json"
    )
    headers = [{"key": "Accept", "value": accept}]
    if (method, path) not in PUBLIC_EXPECTATIONS:
        headers.append(
            {"key": "Authorization", "value": "Bearer invalid.token.for.contract-test"}
        )

    request: dict = {
        "method": method,
        "header": headers,
        "url": "{{base_url}}" + _postman_path(path),
        "description": (
            "Route-contract assertion. Protected operations intentionally use an "
            "invalid bearer and must fail closed before request data is trusted."
        ),
    }
    if method in {"POST", "PUT", "PATCH"} and path != "/api/auth/logout":
        request["header"].append(
            {"key": "Content-Type", "value": "application/json"}
        )
        request["body"] = {
            "mode": "raw",
            "raw": "{}",
            "options": {"raw": {"language": "json"}},
        }

    return {
        "name": f"{method} {path}",
        "request": request,
        "event": [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": _test_script(
                        expected_status=expected_status,
                        path=path,
                    ),
                },
            }
        ],
        "_medflow": {"method": method, "path": path, "expected_status": expected_status},
    }


def build_collection() -> dict:
    schema = app.openapi()
    folders: dict[str, list[dict]] = {}
    path_parameters: set[str] = set()
    for path, operations in sorted(schema["paths"].items()):
        path_parameters.update(re.findall(r"\{([^}]+)\}", path))
        for method_name in HTTP_METHODS:
            if method_name not in operations:
                continue
            operation = operations[method_name]
            tag = (operation.get("tags") or ["other"])[0]
            folders.setdefault(tag, []).append(
                _request_item(method_name.upper(), path, tag)
            )

    return {
        "info": {
            "_postman_id": "f73d118a-3d60-4ee5-82a7-b64adb330bcc",
            "name": "MedFlow All Endpoints Contract",
            "description": (
                "Generated from FastAPI OpenAPI. Every HTTP operation has exact status "
                "and security-header assertions. Run against an isolated migrated "
                "PostgreSQL test environment, never production."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {"name": tag, "item": items}
            for tag, items in sorted(folders.items())
        ],
        "variable": [
            {"key": "base_url", "value": "http://127.0.0.1:8080"},
            *[
                {"key": name, "value": "1"}
                for name in sorted(path_parameters)
            ],
        ],
    }


def main() -> None:
    OUTPUT.write_text(
        json.dumps(build_collection(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
