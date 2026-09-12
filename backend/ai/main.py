import sys
from pathlib import Path

# Add the parent folder of the 'ai' package (i.e., 'backend/') to the python module search path.
# This ensures that imports such as 'from ai.schemas...' work regardless of whether
# the application is run from the 'backend/' folder or directly from the 'backend/ai/' folder.
sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.routes.fraud_routes import router as fraud_router
from ai.routes.safety_routes import router as safety_router
from app.api.dependencies import get_current_active_user
from app.core.config import settings

app = FastAPI(
    title="MedFlow Guardian AI Intelligence Layer",
    description=(
        "Rule-based intelligence engine checking duplicate medications, "
        "allergy conflicts, drug-drug interactions, and prescribing fraud patterns."
    ),
    version="1.0.0",
)

# The standalone AI process is not a separate trust boundary. It reuses the
# MedFlow browser-origin allowlist and authenticated identity dependency rather
# than exposing an anonymous or wildcard-CORS API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

protected_ai_dependencies = [Depends(get_current_active_user)]
app.include_router(
    safety_router,
    prefix="/ai",
    dependencies=protected_ai_dependencies,
)
app.include_router(
    fraud_router,
    prefix="/ai",
    dependencies=protected_ai_dependencies,
)


@app.get("/health", tags=["health"])
async def health_check():
    """Public liveness probe that exposes no patient or clinical data."""
    return {"status": "ok", "module": "ai_intelligence_layer"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
