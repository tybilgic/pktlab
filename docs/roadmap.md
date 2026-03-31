# pktlab Implementation Roadmap

## Purpose

This document is the durable execution plan for implementing `pktlab` from an empty repository to a working MVP. It complements the source brief in [pktlab_c_python_ai_implementation_pack.md](../pktlab_c_python_ai_implementation_pack.md) and translates that architecture into milestones, tickets, and working rules for implementation.

## Locked Decisions

- Target OS: Ubuntu `24.04.4 LTS`
- DPDK target: `25.11.0`
- Controller API stack: `FastAPI + uvicorn + pydantic v2`
- Controller/CLI language: Python `3.11+`
- Datapath language: C
- Controller to datapath transport: Unix domain stream socket with 4-byte big-endian length-prefixed UTF-8 JSON
- `pktlabctl rules replace -f`: standalone rules YAML
- TAP strategy: `pktlab-dpdkd` creates `dtap*` via DPDK TAP PMD, while `pktlab-ctrld` remains topology authority and binds those interfaces into the controller-managed topology after datapath startup

## Resource Profile

The MVP must run on small laptops and small VMs.

- Default datapath worker cores: `1`
- Default DPDK lcores: `"1"`
- Hugepage size: `2MB`
- Hugepage policy: minimum viable amount plus a small safety margin
- Initial default reservation target: `256MB`
- Runtime knobs owned by the controller:
  - `lcores`
  - `hugepages_mb`
  - `burst_size`
  - `rx_queue_size`
  - `tx_queue_size`
  - `mempool_size`

## Milestones

### M1: Foundation And Control Slice

Tickets:
- `PLN-001`
- `PLN-002`
- `PLN-003`
- `PLN-004`
- `PLN-005`

Outcome:
- repo skeleton exists
- schemas are frozen
- C datapath stub exposes basic IPC
- Python controller can supervise the datapath
- CLI `status` works end to end

### M2: Config And Runtime Policy

Tickets:
- `PLN-006`

Outcome:
- topology YAML and standalone rules YAML parse cleanly
- validation is separate from parsing
- effective runtime config is derived conservatively

### M3: Topology Control

Tickets:
- `PLN-007`

Outcome:
- controller can create and destroy namespaces, veths, routes, bridges
- controller starts datapath in `dpdk-host`
- controller waits for `dtap0/dtap1` and binds them into the topology

### M4: Datapath MVP

Tickets:
- `PLN-008`
- `PLN-009`

Outcome:
- datapath starts with TAP PMD
- pass-through forwarding works
- ports, health, and counters are visible through controller and CLI

### M5: Rules And Operations

Tickets:
- `PLN-010`
- `PLN-011`

Outcome:
- atomic ruleset replacement works
- capture management, scenarios, and metrics are available

### M6: Hardening And Release Readiness

Tickets:
- `PLN-012`

Outcome:
- automated tests exist for critical flows
- docs and packaging support repeatable local development
- work can be resumed with low ambiguity

## Architecture Guardrails

- Preserve the three-process model.
- `pktlabctl` only talks to `pktlab-ctrld`.
- Controller owns desired state and topology orchestration.
- Datapath owns fast-path packet processing and counters.
- Topology mutations remain serialized.
- Full-table `replace_rules` is the default synchronization model.
- Capture remains controller-managed.
- Prometheus export remains controller-managed.

## Working Agreement

- Every implementation step should map to one ticket or a clearly scoped sub-slice of a ticket.
- After each completed slice, update [docs/progress.md](progress.md).
- All meaningful changes, including planning and documentation changes, must be recorded in the ordered progress log.
- After each meaningful slice, create a well-scoped commit tied to one ticket or one coherent sub-slice.
- If a slice changes build, test, run, install, or developer workflow, update [README.md](../README.md) in the same slice so the repository entrypoint stays current.
- Commit messages must explain:
  - what the change achieves
  - why it is necessary
  - the preferred approach used
  - tradeoffs versus alternatives when that context matters
- Future sessions should begin by reading:
  - [docs/progress.md](progress.md)
  - the active ticket in [docs/tickets/README.md](tickets/README.md)
  - the latest relevant commit(s)
- If the progress log references a commit for context, read that commit message before continuing work.
- For accuracy, a quick targeted inspection of changed files is still required before continuing work. The tracking docs reduce rediscovery; they do not replace verification.
