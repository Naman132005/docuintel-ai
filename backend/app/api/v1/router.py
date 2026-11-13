"""DocuIntel AI — v1 API route aggregator.

Import endpoint routers here and include them.
Future phases will add one line each (auth, documents, query, …).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

router = APIRouter()

router.include_router(health.router, tags=["health"])
