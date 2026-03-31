# PLN-010 Rules Engine And Atomic Ruleset Replacement

## Status

`not started`

## Goal

Implement full ruleset replacement as the primary synchronization model across controller, datapath, and CLI.

## Why This Exists

This is the core control-plane mutation path for packet behavior and one of the most important architecture constraints in the brief.

## Depends On

- `PLN-006`
- `PLN-008`
- `PLN-009`

## Scope

- implement:
  - `dpdkd/src/rule_table.c`
  - `dpdkd/src/rule_table.h`
  - `dpdkd/src/rules.c`
  - `dpdkd/src/rules.h`
- support IPC commands:
  - `get_rules`
  - `replace_rules`
- wire rule matching into `dpdkd/src/datapath.c`
- implement controller routes:
  - `GET /rules`
  - `PUT /rules`
- implement CLI:
  - `pktlabctl rules show`
  - `pktlabctl rules replace -f <file>`

## Out Of Scope

- incremental rule add/delete as a first-class path
- advanced lock-free synchronization mechanisms

## Implementation Notes

- use a simple array-based rule table
- sort by priority then id
- reject invalid rules without disturbing the active table
- maintain applied rule version explicitly
- keep standalone rules YAML as the CLI file format

## Acceptance Criteria

- invalid rulesets are rejected cleanly
- valid rulesets replace the active table atomically
- rule version and active rules are visible through the controller
- datapath classification uses the active rule table deterministically

## Verification

- unit tests for rule validation and sorting
- integration tests for valid and invalid `replace_rules`
- traffic tests proving rule behavior changes after replacement

## Suggested Commit Slices

- `dpdkd: add rule table and rules validation`
- `dpdkd: wire rules into datapath loop`
- `api: add rules endpoints`
- `ctl: add rules show and replace commands`

## Handoff Note

Do not introduce `add_rule` or `delete_rule` unless the MVP design changes. Keep full-table replacement as the default path.
