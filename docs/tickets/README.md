# Ticket Index

These tickets are the authoritative implementation backlog for the MVP.

## Milestone Mapping

- `M1`
  - [PLN-001 Foundation and Build Tooling](PLN-001-foundation-and-build-tooling.md)
  - [PLN-002 Shared Contracts and Models](PLN-002-shared-contracts-and-models.md)
  - [PLN-003 Datapath IPC Stub in C](PLN-003-datapath-ipc-stub-in-c.md)
  - [PLN-004 Python IPC Client and Controller State](PLN-004-python-ipc-client-and-controller-state.md)
  - [PLN-005 Controller Bootstrap Health API And CLI Status](PLN-005-controller-bootstrap-health-api-and-cli-status.md)
- `M2`
  - [PLN-006 Config Parsing Validation And Effective Runtime Policy](PLN-006-config-parsing-validation-and-effective-runtime-policy.md)
- `M3`
  - [PLN-007 Topology Primitives And TAP Reconciliation](PLN-007-topology-primitives-and-tap-reconciliation.md)
- `M4`
  - [PLN-008 Datapath EAL Ports And Pass-Through Loop](PLN-008-datapath-eal-ports-and-pass-through-loop.md)
  - [PLN-009 Datapath Status Stats And User Surface](PLN-009-datapath-status-stats-and-user-surface.md)
- `M5`
  - [PLN-010 Rules Engine And Atomic Ruleset Replacement](PLN-010-rules-engine-and-atomic-ruleset-replacement.md)
  - [PLN-011 Capture Scenarios And Metrics](PLN-011-capture-scenarios-and-metrics.md)
- `M6`
  - [PLN-012 Tests Packaging Docs And Release Polish](PLN-012-tests-packaging-docs-and-release-polish.md)

## How To Use

- Use one ticket as the active source of truth for the next implementation slice.
- Update [docs/progress.md](../progress.md) when ticket status changes.
- Record every meaningful change in the ordered progress log, even if it only updates planning or documentation.
- If a ticket changes build, test, run, install, or developer workflow, update [README.md](../../README.md) in the same slice.
- Prefer finishing a coherent sub-slice and committing it before switching tickets.
- Each commit should cover one ticket or one coherent sub-slice and use the structured commit message format from [docs/workflow.md](../workflow.md).
