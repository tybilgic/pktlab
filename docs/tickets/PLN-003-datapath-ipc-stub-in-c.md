# PLN-003 Datapath IPC Stub in C

## Status

`not started`

## Goal

Implement a minimal but correct datapath daemon skeleton in C that exposes the required Unix-socket IPC framing and basic health commands.

## Why This Exists

The project needs an end-to-end control slice before topology and forwarding. This ticket establishes the C side of that path.

## Depends On

- `PLN-002`

## Scope

- implement:
  - `dpdkd/src/json_proto.h`
  - `dpdkd/src/json_proto.c`
  - `dpdkd/src/ipc_server.h`
  - `dpdkd/src/ipc_server.c`
  - `dpdkd/src/health.h`
  - `dpdkd/src/health.c`
  - `dpdkd/src/stats.h`
  - `dpdkd/src/stats.c`
  - `dpdkd/src/log.h`
  - `dpdkd/src/log.c`
  - `dpdkd/src/daemon.h`
  - `dpdkd/src/daemon.c`
  - `dpdkd/src/main.c`
- support IPC commands:
  - `ping`
  - `get_version`
  - `get_health`
- return typed error responses for unknown commands and malformed frames

## Out Of Scope

- DPDK port initialization
- packet forwarding
- rules

## Implementation Notes

- keep `main.c` thin
- keep JSON/framing logic out of future hot-path code
- make the daemon start and stay alive even before DPDK fast-path logic exists
- expose explicit health state values from the brief

## Acceptance Criteria

- the daemon creates and listens on `/run/pktlab/dpdkd.sock`
- request/response framing matches the documented 4-byte length prefix protocol
- `ping`, `get_version`, and `get_health` work consistently
- unknown commands return a typed error object

## Verification

- add simple unit or integration coverage for frame encode/decode and request handling
- smoke test with a small hand-crafted client if needed

## Suggested Commit Slices

- `dpdkd: add json framing and IPC server`
- `dpdkd: add health state and daemon entrypoint`

## Handoff Note

Leave the IPC layer cleanly reusable by later commands. Do not bake early control-slice shortcuts into the final server design.
