"""Controller datapath status and stats routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from pktlab_ctrld.error import ErrorCode, PktlabError

from .models import (
    DatapathStatsResetResponseModel,
    DatapathStatsResponseModel,
    DatapathStatusResponseModel,
)

router = APIRouter(prefix="/datapath", tags=["datapath"])


@router.get("/status", response_model=DatapathStatusResponseModel)
def get_datapath_status(request: Request) -> DatapathStatusResponseModel:
    """Return the current datapath runtime view and live ports."""

    controller = request.app.state.controller
    try:
        snapshot = controller.datapath_status_snapshot()
    except PktlabError as exc:
        raise _to_http_exception(exc) from exc
    return DatapathStatusResponseModel.from_snapshot(snapshot)


@router.get("/stats", response_model=DatapathStatsResponseModel)
def get_datapath_stats(request: Request) -> DatapathStatsResponseModel:
    """Return the current datapath counters."""

    controller = request.app.state.controller
    try:
        snapshot = controller.datapath_stats_snapshot()
    except PktlabError as exc:
        raise _to_http_exception(exc) from exc
    return DatapathStatsResponseModel.from_snapshot(snapshot)


@router.post("/stats/reset", response_model=DatapathStatsResetResponseModel)
def reset_datapath_stats(request: Request) -> DatapathStatsResetResponseModel:
    """Reset datapath counters and return the post-reset snapshot."""

    controller = request.app.state.controller
    try:
        result = controller.reset_datapath_stats()
    except PktlabError as exc:
        raise _to_http_exception(exc) from exc
    return DatapathStatsResetResponseModel.from_result(result)


def _to_http_exception(error: PktlabError) -> HTTPException:
    if error.code == ErrorCode.STATE_CONFLICT:
        http_status = status.HTTP_409_CONFLICT
    elif error.code in {
        ErrorCode.DATAPATH_TRANSPORT_ERROR,
        ErrorCode.PROCESS_ERROR,
        ErrorCode.TIMEOUT,
    }:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=http_status, detail=error.to_dict())


__all__ = ["router"]
