# PLN-008 Datapath EAL Ports And Pass-Through Loop

## Status

`in progress`

## Goal

Turn the C stub into a real MVP datapath that starts DPDK, discovers TAP PMD ports, and forwards traffic between ingress and egress.

## Why This Exists

This is the first ticket that delivers packet forwarding, which is the core point of the lab.

## Depends On

- `PLN-003`
- `PLN-006`
- `PLN-007`

## Scope

- implement:
  - `dpdkd/src/eal.c`
  - `dpdkd/src/eal.h`
  - `dpdkd/src/ports.c`
  - `dpdkd/src/ports.h`
  - `dpdkd/src/parser.c`
  - `dpdkd/src/parser.h`
  - `dpdkd/src/actions.c`
  - `dpdkd/src/actions.h`
  - `dpdkd/src/datapath.c`
  - `dpdkd/src/datapath.h`
- start DPDK with TAP PMD devices:
  - `--vdev=net_tap0,iface=dtap0`
  - `--vdev=net_tap1,iface=dtap1`
- implement single-core pass-through forwarding

## Out Of Scope

- rules-based classification
- advanced multi-core tuning
- advanced flow offload

## Implementation Notes

- stay single-worker for MVP
- no heap allocation in the hot path
- no per-packet logging
- keep port naming deterministic and visible to IPC later
- honor conservative runtime defaults from controller config

## Acceptance Criteria

- datapath starts successfully with TAP PMD on Ubuntu 24.04.4
- `dtap0/dtap1` exist and can be bound into the topology
- packets pass from source namespace to sink namespace through the datapath
- health reflects datapath readiness accurately

## Verification

- integration test or repeatable smoke script for pass-through traffic
- datapath startup smoke test with small hugepage footprint

## Suggested Commit Slices

- `dpdkd: add EAL startup and TAP PMD configuration`
- `dpdkd: add port initialization and pass-through datapath loop`

## Handoff Note

Keep this ticket focused on forwarding. Rules come later in `PLN-010`.
