# PLN-004 Python IPC Client and Controller State

## Status

`done`

## Goal

Implement the Python-side datapath protocol helpers, typed client, and explicit desired/observed state models.

## Why This Exists

The controller cannot supervise or reason about the datapath until it can speak the exact framing protocol and hold state explicitly.

## Depends On

- `PLN-002`
- `PLN-003`

## Scope

- implement:
  - `ctrld/pktlab_ctrld/dpdk_client/protocol.py`
  - `ctrld/pktlab_ctrld/dpdk_client/models.py`
  - `ctrld/pktlab_ctrld/dpdk_client/client.py`
  - `ctrld/pktlab_ctrld/state/desired.py`
  - `ctrld/pktlab_ctrld/state/observed.py`
  - `ctrld/pktlab_ctrld/state/reconcile.py`
- support typed client calls for:
  - `ping()`
  - `get_version()`
  - `get_health()`

## Out Of Scope

- HTTP API routes
- topology mutation logic
- advanced reconciliation side effects

## Implementation Notes

- only `protocol.py` should know framing details
- client methods should return typed success/error results
- desired and observed state must stay separate
- reconcile planning should be deterministic and side-effect free

## Acceptance Criteria

- Python client can talk to the C stub daemon successfully
- response validation catches malformed payloads clearly
- state models represent controller and datapath state explicitly
- the groundwork exists for readiness checks and later reconciliation

## Verification

- unit tests for framing helpers
- integration test against the C stub daemon for `ping` and `get_health`

## Completion Note

- the Python IPC/client/state slice is implemented and verified
- full dependency-backed verification completed under the repo virtualenv
- the controller suite passes against the C stub daemon, including the typed IPC client integration
  path
- the next dependent ticket is `PLN-005`

## Suggested Commit Slices

- `ctrld: add dpdk unix socket framing and models`
- `state: add desired observed and reconcile models`

## Handoff Note

Keep REST models out of this ticket. IPC models and REST models should remain separate even if some fields overlap.
