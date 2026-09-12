"""Static certification of the REST authorization surface.

This test complements runtime IDOR/cross-tenant tests by making newly added
resource endpoints fail CI unless they terminate at Model A directly or through
one of the small, reviewed authorization helpers below.
"""

from __future__ import annotations

import ast
from pathlib import Path


API_DIR = Path(__file__).parents[1] / "app" / "api"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
NON_RESOURCE_MODULES = {"auth.py"}
REVIEWED_DELEGATES = {
    "clinical.py": {"_authorize_clinical_access("},
    "consent.py": {"_enforce_consent_write("},
    "interoperability.py": {"_import_canonical_fhir_consent("},
}


def _route_functions(path: Path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        is_http_route = any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr in HTTP_METHODS
            for decorator in node.decorator_list
        )
        if is_http_route:
            yield node.name, ast.get_source_segment(source, node) or ""


def test_every_resource_rest_endpoint_terminates_at_model_a():
    missing = []
    for path in sorted(API_DIR.glob("*.py")):
        if path.name in NON_RESOURCE_MODULES:
            continue
        delegates = REVIEWED_DELEGATES.get(path.name, set())
        for function_name, source in _route_functions(path):
            if ".authorize(" in source:
                continue
            if any(delegate in source for delegate in delegates):
                continue
            missing.append(f"{path.name}:{function_name}")

    assert missing == [], (
        "Resource endpoints without Model A authorization: " + ", ".join(missing)
    )
