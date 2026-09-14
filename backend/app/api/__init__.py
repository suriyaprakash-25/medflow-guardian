# MedFlow Guardian — API routes package
#
# Additive feature routers are composed into the already-mounted route groups so
# the application entry point keeps one authentication, access and FHIR surface.

from app.api import access as access
from app.api import auth as auth
from app.api import interoperability as interoperability
from app.api import access_lifecycle, fhir_binary, oidc

auth.router.include_router(oidc.router, prefix="/oidc")
access.router.include_router(access_lifecycle.router)
interoperability.router.include_router(fhir_binary.router)
