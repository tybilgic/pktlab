# PLN-005 Controller Bootstrap Health API And CLI Status

## Status

`done`

## Goal

Build the first complete user-visible control slice: controller startup, datapath supervision, health API, and CLI `status`.

## Why This Exists

This is the first end-to-end proof that the three-process model works and that the controller hierarchy is preserved.

## Depends On

- `PLN-004`

## Scope

- implement:
  - `ctrld/pktlab_ctrld/process/supervisor.py`
  - `ctrld/pktlab_ctrld/app.py`
  - `ctrld/pktlab_ctrld/api/app.py`
  - `ctrld/pktlab_ctrld/api/models.py`
  - `ctrld/pktlab_ctrld/api/routes_health.py`
  - `ctrld/pktlab_ctrld/main.py`
  - `ctl/pktlabctl/client.py`
  - `ctl/pktlabctl/output.py`
  - `ctl/pktlabctl/commands/status.py`
  - `ctl/pktlabctl/main.py`
  - `ctl/pktlabctl/cli.py`
- define readiness as successful IPC health confirmation, not mere process spawn

## Out Of Scope

- topology apply/destroy
- datapath stats
- rules

## Implementation Notes

- keep route handlers thin
- keep process restart logic explicit and simple
- keep CLI output dual-mode: human-readable default plus `--json`

## Acceptance Criteria

- controller can start and stop cleanly
- controller can supervise the datapath stub
- `GET /health` returns controller and datapath health
- `pktlabctl status` talks only to the controller API and returns useful output

## Verification

- integration test for controller startup and health endpoint
- CLI smoke test against the local controller

## Suggested Commit Slices

- `ctrld: add supervisor and controller app bootstrap`
- `api: add health endpoint`
- `ctl: add controller client and status command`

## Handoff Note

At the end of this ticket, the system should feel alive even though it cannot yet build the full lab topology.

## Completion Notes

- implemented the controller runtime, datapath supervisor, FastAPI `/health` route, and the
  controller entrypoint
- implemented `pktlabctl status` with human-readable and JSON output modes
- added controller and CLI integration tests that exercise a supervised local datapath stub and a
  controller-backed status command path
- verified with:
  - `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests ctl/pktlabctl ctl/tests traffic`
  - `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - `.venv/bin/pktlab-ctrld --help`
  - `.venv/bin/pktlabctl --help`
  - `git diff --check`
- related commits:
  - `012be4d` `ctrld: add datapath supervision and the health API`
  - `fc08760` `ctl: add controller status commands and smoke coverage`
- next ticket: `PLN-006`
