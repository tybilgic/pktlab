"""Controller topology API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from pktlab_ctrld.error import ErrorCode, PktlabError

from .models import TopologyApplyRequestModel, TopologyOperationResponseModel

router = APIRouter(prefix="/topology", tags=["topology"])


@router.post("/apply", response_model=TopologyOperationResponseModel)
def apply_topology(
    payload: TopologyApplyRequestModel,
    request: Request,
) -> TopologyOperationResponseModel:
    """Apply a topology from a controller-visible config path."""

    controller = request.app.state.controller
    try:
        result = controller.apply_topology(payload.config_path)
    except PktlabError as exc:
        raise _to_http_exception(exc) from exc
    return TopologyOperationResponseModel.from_result(result)


@router.post("/destroy", response_model=TopologyOperationResponseModel)
def destroy_topology(request: Request) -> TopologyOperationResponseModel:
    """Destroy the currently applied topology."""

    controller = request.app.state.controller
    try:
        result = controller.destroy_topology()
    except PktlabError as exc:
        raise _to_http_exception(exc) from exc
    return TopologyOperationResponseModel.from_result(result)


def _to_http_exception(error: PktlabError) -> HTTPException:
    if error.code in {ErrorCode.TOPOLOGY_VALIDATION_ERROR, ErrorCode.CONFIG_PARSE_ERROR}:
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif error.code == ErrorCode.STATE_CONFLICT:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=http_status, detail=error.to_dict())


__all__ = ["router"]
