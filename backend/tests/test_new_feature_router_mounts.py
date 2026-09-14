from app.main import app


def test_oidc_fhir_binary_and_cancel_routes_are_mounted():
    # FastAPI may keep internal included-router sentinels in app.routes; only
    # concrete route objects are relevant to the mounted HTTP surface.
    paths = {
        route.path
        for route in app.routes
        if isinstance(getattr(route, "path", None), str)
    }
    assert "/api/auth/oidc/{provider}/challenge" in paths
    assert "/api/auth/oidc/{provider}/exchange" in paths
    assert "/api/interoperability/fhir/Binary/{document_id}" in paths
    assert "/api/access-requests/{request_id}/cancel" in paths
