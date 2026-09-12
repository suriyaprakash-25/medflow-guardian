"""Keep the canonical Postman collection synchronized with the FastAPI surface."""

import json
from pathlib import Path

from app.main import app


COLLECTION = (
    Path(__file__).parents[2]
    / "docs"
    / "postman"
    / "MedFlow-All-Endpoints.postman_collection.json"
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _requests(items):
    for item in items:
        if "request" in item:
            yield item
        yield from _requests(item.get("item", []))


def test_postman_collection_covers_every_http_operation_with_assertions():
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    items = list(_requests(collection["item"]))
    actual = {
        (item["_medflow"]["method"], item["_medflow"]["path"])
        for item in items
    }
    expected = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in HTTP_METHODS
    }

    assert actual == expected
    assert len(items) == len(actual), "Duplicate endpoint requests in Postman collection"
    for item in items:
        test_events = [
            event for event in item.get("event", []) if event.get("listen") == "test"
        ]
        assert test_events, f"Missing Postman assertion: {item['name']}"
        script = "\n".join(test_events[0]["script"]["exec"])
        assert "pm.response.to.have.status" in script
        assert "security headers are present" in script


def test_no_postman_collection_uses_removed_auth_token_route():
    postman_dir = COLLECTION.parent
    offenders = []
    for path in postman_dir.glob("*.postman_collection.json"):
        if "/api/auth/token" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)
    assert offenders == []


def test_every_postman_collection_has_executable_assertions():
    for path in COLLECTION.parent.glob("*.postman_collection.json"):
        collection = json.loads(path.read_text(encoding="utf-8"))
        collection_tests = [
            event
            for event in collection.get("event", [])
            if event.get("listen") == "test"
        ]
        for item in _requests(collection.get("item", [])):
            item_tests = [
                event
                for event in item.get("event", [])
                if event.get("listen") == "test"
            ]
            assert collection_tests or item_tests, (
                f"Postman request has no effective assertion: {path.name}:{item['name']}"
            )
