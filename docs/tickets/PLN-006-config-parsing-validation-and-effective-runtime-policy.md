# PLN-006 Config Parsing Validation And Effective Runtime Policy

## Status

`done`

## Goal

Implement clean topology and rules parsing, structured validation, and a conservative effective runtime policy for small machines.

## Why This Exists

The controller needs authoritative desired state, and the project has explicit low-resource constraints that must be encoded early.

## Depends On

- `PLN-002`
- `PLN-005`

## Scope

- implement:
  - `ctrld/pktlab_ctrld/config/topology.py`
  - `ctrld/pktlab_ctrld/config/rules.py`
  - `ctrld/pktlab_ctrld/config/validation.py`
- define controller logic for deriving effective runtime values when optional fields are omitted
- validate:
  - unique names
  - route references
  - IP/CIDR formats
  - action target references
  - explicit `default_action`
  - supported protocols and actions
- include effective defaults for:
  - `lcores`
  - `hugepages_mb`
  - `burst_size`
  - queue sizing
  - mempool sizing

## Out Of Scope

- executing topology mutations
- datapath EAL wiring

## Implementation Notes

- parsing and validation must remain separate
- use pydantic for config-facing models
- keep runtime policy understandable; avoid opaque formulas
- expose both requested and effective values to the controller state

## Acceptance Criteria

- topology YAML and standalone rules YAML parse successfully
- invalid configs return structured errors
- omitted runtime knobs produce safe conservative defaults
- obviously oversized values can be rejected or flagged clearly

## Verification

- unit tests for valid and invalid YAML cases
- unit tests for effective runtime policy derivation

## Suggested Commit Slices

- `config: add topology and rules parsers`
- `config: add validation and effective runtime policy`

## Handoff Note

This ticket should make the later topology manager mostly procedural. By the time `PLN-007` starts, desired state should already be trustworthy.

## Completion Notes

- implemented topology and standalone rules YAML loaders in:
  - `ctrld/pktlab_ctrld/config/topology.py`
  - `ctrld/pktlab_ctrld/config/rules.py`
- implemented semantic validation and effective runtime derivation in `ctrld/pktlab_ctrld/config/validation.py`
- extended controller state models so requested and effective datapath runtime settings can be carried forward into later topology work
- added unit coverage for valid and invalid parsing, semantic issue aggregation, runtime derivation, and controller state exposure
- verified with:
  - `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - `.venv/bin/python -m unittest discover -s ctrld/tests/unit -t ctrld -v`
  - `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - `git diff --check`
- related commits:
  - `e26821b` `config: add topology and rules validation with conservative runtime defaults`
- next ticket: `PLN-007`
