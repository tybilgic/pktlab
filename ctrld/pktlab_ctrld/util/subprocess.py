"""Centralized subprocess helpers for controller-owned system mutations."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence

from pktlab_ctrld.error import ProcessExecutionError


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Normalized subprocess result used across topology helpers."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandExecutor:
    """Run subprocess commands and normalize failures into typed project errors."""

    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._runner = runner

    def run(
        self,
        argv: Sequence[str],
        *,
        allowed_returncodes: Sequence[int] = (0,),
        cwd: str | None = None,
    ) -> CommandResult:
        command = tuple(argv)
        completed = self._runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        result = CommandResult(
            argv=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if result.returncode not in set(allowed_returncodes):
            raise ProcessExecutionError(
                "subprocess command failed",
                context={
                    "argv": list(result.argv),
                    "returncode": result.returncode,
                    "stdout": result.stdout or None,
                    "stderr": result.stderr or None,
                },
            )
        return result


__all__ = ["CommandExecutor", "CommandResult"]
