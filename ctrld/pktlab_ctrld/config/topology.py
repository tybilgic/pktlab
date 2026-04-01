"""Topology configuration parsing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from pktlab_ctrld.error import ConfigParseError
from pktlab_ctrld.types import TopologyConfigModel


def load_topology_config(path: str | Path) -> TopologyConfigModel:
    """Load a topology configuration document from disk."""

    source_path = Path(path)
    try:
        text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigParseError(
            "unable to read topology config",
            context={"source": str(source_path), "detail": str(exc)},
        ) from exc
    return parse_topology_config_text(text, source=str(source_path))


def parse_topology_config_text(
    text: str,
    *,
    source: str = "<memory>",
) -> TopologyConfigModel:
    """Parse a topology configuration YAML document into the shared model."""

    payload = _load_yaml_mapping(text, source=source, document_name="topology config")
    try:
        return TopologyConfigModel.model_validate(payload)
    except PydanticValidationError as exc:
        raise ConfigParseError(
            "topology config structure is invalid",
            context={
                "source": source,
                "issues": _serialize_pydantic_errors(exc),
            },
        ) from exc


def _load_yaml_mapping(
    text: str,
    *,
    source: str,
    document_name: str,
) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigParseError(
            f"{document_name} YAML could not be parsed",
            context={"source": source, "detail": str(exc)},
        ) from exc

    if payload is None:
        raise ConfigParseError(
            f"{document_name} is empty",
            context={"source": source},
        )
    if not isinstance(payload, dict):
        raise ConfigParseError(
            f"{document_name} must be a mapping at the document root",
            context={"source": source, "root_type": type(payload).__name__},
        )

    return payload


def _serialize_pydantic_errors(error: PydanticValidationError) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for item in error.errors():
        path = ".".join(str(part) for part in item["loc"]) or "$"
        issues.append(
            {
                "path": path,
                "code": item["type"],
                "message": item["msg"],
            }
        )
    return issues


__all__ = ["load_topology_config", "parse_topology_config_text"]
