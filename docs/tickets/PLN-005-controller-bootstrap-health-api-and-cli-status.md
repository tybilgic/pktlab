# PLN-005 Controller Bootstrap Health API And CLI Status

## Status

`not started`

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
