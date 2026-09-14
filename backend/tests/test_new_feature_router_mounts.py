from app.main import app


def test_oidc_fhir_binary_and_cancel_routes_are_mounted():
    paths = {route.path for route in app.routes}
    assert "/api/auth/oidc/{provider}/challenge" in paths
    assert "/api/auth/oidc/{provider}/exchange" in paths
    assert "/api/interoperability/fhir/Binary/{document_id}" in paths
    assert "/api/access-requests/{request_id}/cancel" in paths
