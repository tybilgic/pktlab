"""HTTP client for talking to pktlab-ctrld."""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ControllerStatusModel(BaseModel):
    """Controller section of the health API."""

    model_config = ConfigDict(extra="forbid")

    service: str = Field(min_length=1)
    version: str = Field(min_length=1)
    state: str = Field(min_length=1)
    message: str = Field(min_length=1)


class DatapathStatusModel(BaseModel):
    """Datapath section of the health API."""

    model_config = ConfigDict(extra="forbid")

    managed: bool
    reachable: bool
    socket_path: str = Field(min_length=1)
    pid: int | None = Field(default=None, ge=1)
    exit_code: int | None = None
    last_error: str | None = None
    service: str | None = None
    version: str | None = None
    dpdk_version: str | None = None
    state: str | None = None
    message: str | None = None
    applied_rule_version: int | None = Field(default=None, ge=0)
    ports_ready: bool = False
    paused: bool = False


class HealthResponseModel(BaseModel):
    """Typed `/health` response used by the CLI."""

    model_config = ConfigDict(extra="forbid")

    controller: ControllerStatusModel
    datapath: DatapathStatusModel


class DatapathPortModel(BaseModel):
    """Single datapath port entry returned by the controller."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    port_id: int = Field(ge=0)
    role: str = Field(min_length=1)
    state: str = Field(min_length=1)


class DatapathStatusResponseModel(BaseModel):
    """Typed `/datapath/status` response used by the CLI."""

    model_config = ConfigDict(extra="forbid")

    controller: ControllerStatusModel
    datapath: DatapathStatusModel
    ports: list[DatapathPortModel]


class DatapathStatsModel(BaseModel):
    """Typed datapath counters used by the CLI."""

    model_config = ConfigDict(extra="forbid")

    rx_packets: int = Field(ge=0)
    tx_packets: int = Field(ge=0)
    drop_packets: int = Field(ge=0)
    drop_parse_errors: int = Field(ge=0)
    drop_no_match: int = Field(ge=0)
    rx_bursts: int = Field(ge=0)
    tx_bursts: int = Field(ge=0)
    unsent_packets: int = Field(ge=0)
    rule_hits: dict[str, int] = Field(default_factory=dict)


class DatapathStatsResponseModel(BaseModel):
    """Typed `/datapath/stats` response used by the CLI."""

    model_config = ConfigDict(extra="forbid")

    datapath: DatapathStatusModel
    stats: DatapathStatsModel


class TopologyOperationResponseModel(BaseModel):
    """Typed topology lifecycle response used by the CLI."""

    model_config = ConfigDict(extra="forbid")

    operation: str = Field(min_length=1)
    topology_name: str | None = None
    config_path: str | None = None
    applied: bool
    datapath_namespace: str | None = None
    datapath_running: bool
    message: str = Field(min_length=1)


class ControllerClientError(RuntimeError):
    """Raised when the CLI cannot fetch or parse controller responses."""


class ControllerClient:
    """Minimal HTTP client for pktlab controller endpoints."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 2.0,
        client_factory: Callable[..., httpx.Client] = httpx.Client,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client_factory = client_factory

    def get_health(self) -> HealthResponseModel:
        """Fetch the controller health document."""

        response = self._request_json("GET", "/health")
        try:
            return HealthResponseModel.model_validate(response)
        except ValidationError as exc:
            raise ControllerClientError(
                f"controller health response did not match the expected schema: {exc}"
            ) from exc

    def get_datapath_status(self) -> DatapathStatusResponseModel:
        """Fetch the controller datapath status document."""

        response = self._request_json("GET", "/datapath/status")
        try:
            return DatapathStatusResponseModel.model_validate(response)
        except ValidationError as exc:
            raise ControllerClientError(
                f"controller datapath status response did not match the expected schema: {exc}"
            ) from exc

    def get_datapath_stats(self) -> DatapathStatsResponseModel:
        """Fetch the controller datapath stats document."""

        response = self._request_json("GET", "/datapath/stats")
        try:
            return DatapathStatsResponseModel.model_validate(response)
        except ValidationError as exc:
            raise ControllerClientError(
                f"controller datapath stats response did not match the expected schema: {exc}"
            ) from exc

    def apply_topology(self, config_path: str) -> TopologyOperationResponseModel:
        """Request topology apply through the controller API."""

        if not config_path.strip():
            raise ValueError("config_path must be a non-empty string")
        response = self._request_json("POST", "/topology/apply", json_body={"config_path": config_path})
        try:
            return TopologyOperationResponseModel.model_validate(response)
        except ValidationError as exc:
            raise ControllerClientError(
                f"controller topology apply response did not match the expected schema: {exc}"
            ) from exc

    def destroy_topology(self) -> TopologyOperationResponseModel:
        """Request topology destroy through the controller API."""

        response = self._request_json("POST", "/topology/destroy", json_body={})
        try:
            return TopologyOperationResponseModel.model_validate(response)
        except ValidationError as exc:
            raise ControllerClientError(
                f"controller topology destroy response did not match the expected schema: {exc}"
            ) from exc

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            with self._client_factory(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.request(method, path, json=json_body)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                payload = exc.response.json()
                if isinstance(payload, dict):
                    raw_detail = payload.get("detail")
                    if raw_detail is not None:
                        detail = f": {raw_detail}"
            except Exception:
                detail = ""
            raise ControllerClientError(
                f"controller returned HTTP {exc.response.status_code} for {path}{detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ControllerClientError(f"controller request failed for {path}: {exc}") from exc

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ControllerClientError("controller returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise ControllerClientError("controller returned a non-object JSON payload")
        return payload


__all__ = [
    "ControllerClient",
    "ControllerClientError",
    "ControllerStatusModel",
    "DatapathPortModel",
    "DatapathStatusModel",
    "DatapathStatusResponseModel",
    "DatapathStatsModel",
    "DatapathStatsResponseModel",
    "HealthResponseModel",
    "TopologyOperationResponseModel",
]
