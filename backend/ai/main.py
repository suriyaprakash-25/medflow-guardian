import sys
from pathlib import Path

# Add the parent folder of the 'ai' package (i.e., 'backend/') to the python module search path.
# This ensures that imports such as 'from ai.schemas...' work regardless of whether
# the application is run from the 'backend/' folder or directly from the 'backend/ai/' folder.
sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai.routes.safety_routes import router as safety_router
from ai.routes.fraud_routes import router as fraud_router

app = FastAPI(
    title="MedFlow Guardian AI Intelligence Layer",
    description=(
        "Rule-based intelligence engine checking duplicate medications, "
        "allergy conflicts, drug-drug interactions, and prescribing fraud patterns."
    ),
    version="1.0.0"
)

# Configure CORS (permissible origins allowed for hackathon/testing flexibility)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount APIRouters under the '/ai' prefix
app.include_router(safety_router, prefix="/ai")
app.include_router(fraud_router, prefix="/ai")

@app.get("/health", tags=["health"])
async def health_check():
    """Simple API health probe."""
    return {"status": "ok", "module": "ai_intelligence_layer"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
