"""
Healthcheck API router.

Lightweight endpoint to verify the API operational status.
Useful for load balancers, Kubernetes probes, and monitoring tools.
"""

from fastapi import APIRouter, status

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Healthcheck",
    response_description="Current API operational status",
)
async def healthcheck() -> dict[str, str]:
    """Returns operational status of the API."""
    return {"status": "ok", "service": "novaextract-ai"}
