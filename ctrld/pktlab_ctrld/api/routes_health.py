"""Controller health API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from .models import HealthResponseModel

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponseModel)
def get_health(request: Request) -> HealthResponseModel:
    """Return controller and datapath runtime health."""

    controller = request.app.state.controller
    return HealthResponseModel.from_snapshot(controller.health_snapshot())
