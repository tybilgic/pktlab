# PLN-001 Foundation and Build Tooling

## Status

`not started`

## Goal

Create the repository skeleton and build entry points so all later work lands into a stable structure instead of ad hoc files.

## Why This Exists

The implementation pack defines a precise layout and root build surface. This ticket creates that structure first so later tickets can focus on functionality instead of scaffolding.

## Depends On

- none

## Scope

- create the directory layout from the implementation pack
- add root files: `README.md`, `LICENSE`, `.gitignore`, root `pyproject.toml`, `Makefile`
- add package scaffolding for:
  - `dpdkd/meson.build`
  - `ctrld/pyproject.toml`
  - `ctl/pyproject.toml`
- create empty Python package directories with `__init__.py` where appropriate
- create placeholder docs directories from the brief

## Out Of Scope

- implementing functional code
- filling every document in `docs/`
- wiring complete dependencies

## Implementation Notes

- mirror the repository layout from the brief closely
- make the root `Makefile` orchestration-only
- use Python `3.11+`
- keep package config minimal and readable

## Required Files

- `README.md`
- `Makefile`
- `pyproject.toml`
- `dpdkd/meson.build`
- `ctrld/pyproject.toml`
- `ctl/pyproject.toml`

## Acceptance Criteria

- the repository tree matches the intended project shape
- required root make targets exist, even if some are placeholders initially
- Python packages are importable at a package-structure level
- build config files exist in the expected locations

## Verification

- list the resulting tree and compare to the target structure
- run a minimal packaging/build sanity check where possible without full implementation

## Suggested Commit Slices

- `repo: add initial project skeleton and root tooling`
- `build: add meson and python package scaffolding`

## Handoff Note

Do `PLN-001` and `PLN-002` back to back if possible. The schemas and the tree layout should land early together.
