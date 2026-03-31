# PLN-012 Tests Packaging Docs And Release Polish

## Status

`not started`

## Goal

Add enough testing, packaging polish, and operator documentation to make the MVP repeatable and maintainable.

## Why This Exists

The earlier tickets deliver functionality. This ticket makes the result usable by someone who did not build it from memory.

## Depends On

- `PLN-005`
- `PLN-007`
- `PLN-009`
- `PLN-010`
- `PLN-011`

## Scope

- add unit tests for:
  - IPC framing
  - config parsing and validation
  - rules validation and sorting
- add integration tests for:
  - controller supervising datapath
  - topology apply/destroy
  - pass-through traffic
  - rules replacement
  - capture lifecycle
- improve packaging and local setup docs
- fill essential project docs:
  - architecture
  - process model
  - topology
  - IPC
  - controller
  - observability

## Out Of Scope

- distributed deployment
- production-grade auth and RBAC

## Implementation Notes

- prioritize critical path tests before broad coverage
- keep docs aligned with the actual implementation, not the aspirational design
- make local development steps straightforward on Ubuntu 24.04.4

## Acceptance Criteria

- the root make targets are useful and not just placeholders
- a fresh developer can follow the docs to build and run the MVP
- automated tests cover the critical control and datapath flows

## Verification

- run the intended test suites
- follow the docs from a clean environment where possible

## Suggested Commit Slices

- `test: add unit coverage for contracts and parsing`
- `test: add integration coverage for control and datapath flows`
- `docs: add operator and developer documentation`

## Handoff Note

This ticket should be used repeatedly near the end of each milestone as hardening work, not only at the absolute end of the project.
