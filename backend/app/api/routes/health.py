"""
Health-check router.
"""

import logging
from fastapi import APIRouter
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()
