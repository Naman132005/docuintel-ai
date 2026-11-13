"""DocuIntel AI — FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# ── CORS middleware ───────────────────────────────
# Allows the React frontend (and any other listed origins)
# to make requests to this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API routes ──────────────────────────────
app.include_router(v1_router, prefix=settings.API_V1_STR)


@app.get("/")
def root() -> dict:
    """Root endpoint — confirms the API is reachable."""
    return {"message": f"{settings.PROJECT_NAME} API"}
