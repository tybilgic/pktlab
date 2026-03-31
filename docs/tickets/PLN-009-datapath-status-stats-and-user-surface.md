# PLN-009 Datapath Status Stats And User Surface

## Status

`not started`

## Goal

Expose datapath runtime information through IPC, controller API, and CLI so the lab is observable during development and operation.

## Why This Exists

Once packets flow, users need to inspect datapath state without talking to the datapath directly.

## Depends On

- `PLN-008`

## Scope

- extend C IPC with:
  - `get_ports`
  - `get_stats`
  - `reset_stats`
  - `pause_datapath`
  - `resume_datapath`
  - `shutdown`
- extend Python client models and methods for those commands
- implement controller routes:
  - `GET /datapath/status`
  - `GET /datapath/stats`
- implement CLI user surface:
  - `pktlabctl status`
  - `pktlabctl stats show`

## Out Of Scope

- rules management
- Prometheus export

## Implementation Notes

- datapath status and controller status are related but not identical
- preserve typed errors for all IPC calls
- keep CLI output concise but useful

## Acceptance Criteria

- users can inspect ports and counters through the controller
- pause and resume semantics are explicit and reflected in health
- stats reset works and is observable

## Verification

- integration tests for status and stats endpoints
- CLI smoke tests for human-readable and `--json` output

## Suggested Commit Slices

- `dpdkd: add runtime status and stats IPC commands`
- `ctrld: add datapath status and stats routes`
- `ctl: add stats display`

## Handoff Note

If pause/resume semantics are not stable yet, land the read-only status surface first and add write actions in a follow-up sub-slice.
