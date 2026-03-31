# PLN-007 Topology Primitives And TAP Reconciliation

## Status

`not started`

## Goal

Implement controller-owned topology lifecycle, including the special reconciliation step that binds datapath-created TAP PMD interfaces into the lab topology.

## Why This Exists

This is the project-specific ownership split: the controller owns the topology, but the datapath creates `dtap*`. This ticket makes that boundary explicit in code.

## Depends On

- `PLN-005`
- `PLN-006`

## Scope

- implement utility wrappers:
  - `ctrld/pktlab_ctrld/util/subprocess.py`
  - `ctrld/pktlab_ctrld/util/netns.py`
  - `ctrld/pktlab_ctrld/util/time.py`
- implement topology modules:
  - `ctrld/pktlab_ctrld/topology/namespaces.py`
  - `ctrld/pktlab_ctrld/topology/links.py`
  - `ctrld/pktlab_ctrld/topology/routes.py`
  - `ctrld/pktlab_ctrld/topology/taps.py`
  - `ctrld/pktlab_ctrld/topology/manager.py`
- implement topology API/CLI surface:
  - `ctrld/pktlab_ctrld/api/routes_topology.py`
  - `ctl/pktlabctl/commands/topology.py`

## Required Topology Order

1. create namespaces
2. create veth pairs
3. move/configure interfaces
4. create `br-in` and `br-out` in `dpdk-host`
5. program routes
6. start `pktlab-dpdkd` in `dpdk-host`
7. wait for `dtap0` and `dtap1`
8. attach `veth-in-k + dtap0` to `br-in`
9. attach `dtap1 + veth-out-k` to `br-out`
10. bring links and bridges up

## Out Of Scope

- packet forwarding logic
- rules

## Implementation Notes

- all shell command execution must go through centralized wrappers
- topology apply must be serialized
- destroy must be reverse-safe and clear about partial failures
- do not create TAPs from the controller; only reconcile them after datapath startup

## Acceptance Criteria

- `POST /topology/apply` creates the lab deterministically
- `POST /topology/destroy` removes the lab safely
- bridges and TAP attachments are visible in `dpdk-host`
- repeated apply/destroy attempts behave predictably and log clearly

## Verification

- integration tests for apply/destroy
- smoke verification of interface existence and bridge membership inside namespaces

## Suggested Commit Slices

- `util: add subprocess and netns helpers`
- `topology: add namespace veth and route management`
- `topology: add tap reconciliation and apply destroy orchestration`
- `api: add topology apply and destroy routes`

## Handoff Note

The bridge-based binding model is intentional. Do not replace it with TAP PMD `remote=` unless the design changes explicitly.
