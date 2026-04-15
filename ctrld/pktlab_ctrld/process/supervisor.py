"""Launch and monitor the pktlab datapath daemon."""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable

from pktlab_ctrld.dpdk_client.client import DpdkClient
from pktlab_ctrld.dpdk_client.models import (
    AckPayload,
    CommandResult,
    HealthStateModel,
    PortsPayload,
    StatsPayload,
    VersionPayload,
)
from pktlab_ctrld.error import DatapathTransportError, ProcessExecutionError


@dataclass(frozen=True, slots=True)
class SupervisorConfig:
    """Static launch configuration for the datapath subprocess."""

    dpdkd_binary: str
    socket_path: str
    launch_prefix: tuple[str, ...] = ()
    extra_args: tuple[str, ...] = ()
    startup_timeout_seconds: float = 5.0
    poll_interval_seconds: float = 0.05
    shutdown_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not self.dpdkd_binary.strip():
            raise ValueError("dpdkd_binary must be a non-empty string")
        if not self.socket_path.strip():
            raise ValueError("socket_path must be a non-empty string")
        if any(not token.strip() for token in self.launch_prefix):
            raise ValueError("launch_prefix must not contain empty elements")
        if any(not token.strip() for token in self.extra_args):
            raise ValueError("extra_args must not contain empty elements")
        if self.startup_timeout_seconds <= 0:
            raise ValueError("startup_timeout_seconds must be greater than zero")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than zero")
        if self.shutdown_timeout_seconds <= 0:
            raise ValueError("shutdown_timeout_seconds must be greater than zero")


@dataclass(frozen=True, slots=True)
class DatapathProcessStatus:
    """Current supervisor view of the datapath process."""

    managed: bool
    socket_path: str
    pid: int | None = None
    running: bool = False
    reachable: bool = False
    exit_code: int | None = None
    last_error: str | None = None
    version: VersionPayload | None = None
    health: HealthStateModel | None = None


class DpdkdSupervisor:
    """Simple process supervisor for the datapath daemon."""

    def __init__(
        self,
        config: SupervisorConfig,
        *,
        client_factory: Callable[[str], DpdkClient] = DpdkClient,
        popen_factory: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
    ) -> None:
        self.config = config
        self._client_factory = client_factory
        self._popen_factory = popen_factory
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self._client: DpdkClient | None = None
        self._last_version: VersionPayload | None = None
        self._last_health: HealthStateModel | None = None
        self._last_error: str | None = None
        self._last_exit_code: int | None = None

    def start(self) -> DatapathProcessStatus:
        """Spawn the datapath process and wait until IPC health is reachable."""

        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self._wait_for_ready_locked()

            self._last_version = None
            self._last_health = None
            self._last_error = None
            self._last_exit_code = None

            command = [
                *self.config.launch_prefix,
                self.config.dpdkd_binary,
                "--socket-path",
                self.config.socket_path,
                *self.config.extra_args,
            ]
            self._process = self._popen_factory(
                command,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
            )
            self._client = self._client_factory(self.config.socket_path)
            try:
                return self._wait_for_ready_locked()
            except Exception:
                self._stop_locked(clear_history=False)
                raise

    def status(self) -> DatapathProcessStatus:
        """Return the current datapath process view."""

        with self._lock:
            return self._status_locked()

    def get_ports(self) -> CommandResult[PortsPayload]:
        """Fetch the live datapath port status over IPC."""

        with self._lock:
            status = self._status_locked()
            if not status.reachable:
                raise DatapathTransportError(
                    "datapath IPC is not reachable for port status",
                    context={"socket_path": self.config.socket_path},
                )
            return self._require_client_locked().get_ports()

    def get_stats(self) -> CommandResult[StatsPayload]:
        """Fetch the live datapath counters over IPC."""

        with self._lock:
            status = self._status_locked()
            if not status.reachable:
                raise DatapathTransportError(
                    "datapath IPC is not reachable for stats",
                    context={"socket_path": self.config.socket_path},
                )
            return self._require_client_locked().get_stats()

    def reset_stats(self) -> CommandResult[AckPayload]:
        """Reset the live datapath counters over IPC."""

        with self._lock:
            status = self._status_locked()
            if not status.reachable:
                raise DatapathTransportError(
                    "datapath IPC is not reachable for stats reset",
                    context={"socket_path": self.config.socket_path},
                )
            return self._require_client_locked().reset_stats()

    def pause_datapath(self) -> CommandResult[AckPayload]:
        """Pause the live datapath forwarding loop over IPC."""

        with self._lock:
            status = self._status_locked()
            if not status.reachable:
                raise DatapathTransportError(
                    "datapath IPC is not reachable for pause",
                    context={"socket_path": self.config.socket_path},
                )
            return self._require_client_locked().pause_datapath()

    def resume_datapath(self) -> CommandResult[AckPayload]:
        """Resume the live datapath forwarding loop over IPC."""

        with self._lock:
            status = self._status_locked()
            if not status.reachable:
                raise DatapathTransportError(
                    "datapath IPC is not reachable for resume",
                    context={"socket_path": self.config.socket_path},
                )
            return self._require_client_locked().resume_datapath()

    def stop(self) -> None:
        """Terminate the datapath subprocess if it is running."""

        with self._lock:
            self._stop_locked(clear_history=True)

    def _wait_for_ready_locked(self) -> DatapathProcessStatus:
        deadline = time.monotonic() + self.config.startup_timeout_seconds
        while time.monotonic() < deadline:
            process = self._process
            if process is None:
                raise ProcessExecutionError(
                    "datapath process state was lost during startup",
                    context={"socket_path": self.config.socket_path},
                )

            exit_code = process.poll()
            if exit_code is not None:
                stderr = self._consume_stderr_locked(process)
                self._last_exit_code = exit_code
                self._last_error = stderr or "datapath process exited before readiness"
                raise ProcessExecutionError(
                    "datapath process exited before readiness was confirmed",
                    context={
                        "binary_path": self.config.dpdkd_binary,
                        "socket_path": self.config.socket_path,
                        "exit_code": exit_code,
                        "stderr": stderr or None,
                    },
                )

            try:
                return self._refresh_ipc_state_locked(process)
            except DatapathTransportError as exc:
                self._last_error = exc.message
                time.sleep(self.config.poll_interval_seconds)

        raise ProcessExecutionError(
            "timed out waiting for datapath IPC readiness",
            context={
                "binary_path": self.config.dpdkd_binary,
                "socket_path": self.config.socket_path,
                "timeout_seconds": self.config.startup_timeout_seconds,
            },
        )

    def _status_locked(self) -> DatapathProcessStatus:
        process = self._process
        if process is None:
            return DatapathProcessStatus(
                managed=True,
                socket_path=self.config.socket_path,
                exit_code=self._last_exit_code,
                last_error=self._last_error,
                version=self._last_version,
                health=self._last_health,
            )

        exit_code = process.poll()
        if exit_code is not None:
            stderr = self._consume_stderr_locked(process)
            self._last_exit_code = exit_code
            self._last_error = stderr or self._last_error or "datapath process exited unexpectedly"
            self._process = None
            self._client = None
            return DatapathProcessStatus(
                managed=True,
                socket_path=self.config.socket_path,
                exit_code=exit_code,
                last_error=self._last_error,
                version=self._last_version,
                health=self._last_health,
            )

        try:
            return self._refresh_ipc_state_locked(process)
        except DatapathTransportError as exc:
            self._last_error = exc.message
            return DatapathProcessStatus(
                managed=True,
                socket_path=self.config.socket_path,
                pid=process.pid,
                running=True,
                reachable=False,
                last_error=self._last_error,
                version=self._last_version,
                health=self._last_health,
            )

    def _refresh_ipc_state_locked(
        self,
        process: subprocess.Popen[str],
    ) -> DatapathProcessStatus:
        client = self._require_client_locked()

        ping_result = client.ping()
        if not ping_result.ok:
            error = ping_result.error
            message = f"datapath readiness ping failed: {error.code.value}: {error.message}"
            self._last_error = message
            raise ProcessExecutionError(
                message,
                context={
                    "socket_path": self.config.socket_path,
                    "error": error.model_dump(mode="json"),
                },
            )

        health_result = client.get_health()
        if not health_result.ok:
            error = health_result.error
            message = f"datapath health check failed: {error.code.value}: {error.message}"
            self._last_error = message
            raise ProcessExecutionError(
                message,
                context={
                    "socket_path": self.config.socket_path,
                    "error": error.model_dump(mode="json"),
                },
            )

        version_result = client.get_version()
        if not version_result.ok:
            error = version_result.error
            message = f"datapath version check failed: {error.code.value}: {error.message}"
            self._last_error = message
            raise ProcessExecutionError(
                message,
                context={
                    "socket_path": self.config.socket_path,
                    "error": error.model_dump(mode="json"),
                },
            )

        self._last_health = health_result.unwrap().health
        self._last_version = version_result.unwrap()
        self._last_error = None
        self._last_exit_code = None
        return DatapathProcessStatus(
            managed=True,
            socket_path=self.config.socket_path,
            pid=process.pid,
            running=True,
            reachable=True,
            version=self._last_version,
            health=self._last_health,
        )

    def _stop_locked(self, *, clear_history: bool) -> None:
        process = self._process
        self._process = None
        self._client = None

        if process is None:
            if clear_history:
                self._last_version = None
                self._last_health = None
                self._last_error = None
                self._last_exit_code = None
            return

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self.config.shutdown_timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=self.config.shutdown_timeout_seconds)

        self._consume_stderr_locked(process)
        if clear_history:
            self._last_version = None
            self._last_health = None
            self._last_error = None
            self._last_exit_code = None

    def _consume_stderr_locked(self, process: subprocess.Popen[str]) -> str:
        if process.stderr is None or process.stderr.closed:
            return ""
        try:
            content = process.stderr.read().strip()
        finally:
            process.stderr.close()
        return content

    def _require_client_locked(self) -> DpdkClient:
        if self._client is None:
            raise ProcessExecutionError(
                "datapath client is not initialized",
                context={"socket_path": self.config.socket_path},
            )
        return self._client


__all__ = ["DatapathProcessStatus", "DpdkdSupervisor", "SupervisorConfig"]
