# PLN-002 Shared Contracts and Models

## Status

`done`

## Goal

Freeze the shared interfaces early so the C datapath and Python control plane implement the same contract.

## Why This Exists

The brief is explicit about not inventing fields or silently renaming structures. This ticket makes the schemas and shared model definitions the foundation for all later work.

## Depends On

- `PLN-001`

## Scope

- create `schemas/dpdkd-ipc.schema.json`
- create `schemas/topology.schema.yaml`
- create C public headers:
  - `dpdkd/include/pktlab_dpdkd/types.h`
  - `dpdkd/include/pktlab_dpdkd/errors.h`
  - `dpdkd/include/pktlab_dpdkd/version.h`
- create Python shared model/error files:
  - `ctrld/pktlab_ctrld/types.py`
  - `ctrld/pktlab_ctrld/error.py`

## Out Of Scope

- socket logic
- YAML parsing implementation
- controller REST handlers

## Implementation Notes

- keep field names identical to the brief
- include required IPC commands and envelopes
- include topology process config for conservative runtime knobs
- separate external contracts from runtime-only state

## Required Decisions Already Locked

- standalone rules files for CLI replacement
- TAP PMD strategy with controller-owned topology reconciliation
- low-resource runtime knobs exposed through controller config

## Acceptance Criteria

- the schema files cover the required commands and config objects
- C shared headers define the core public structures and error codes
- Python shared models are suitable for later parser/client work
- no contract ambiguity remains for the first implementation slice

## Verification

- manually compare schema field names and enums against the brief
- ensure the same message shapes can be represented in both C and Python

## Suggested Commit Slices

- `schemas: add initial IPC and topology contracts`
- `shared: add C and Python core type definitions`

## Handoff Note

This ticket should leave enough clarity for `PLN-003` and `PLN-004` to proceed without revisiting the brief line by line.
