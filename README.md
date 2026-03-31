# pktlab

`pktlab` is a small packet-processing lab built around a Python control plane and a C datapath.

The repository is being implemented in ticketed slices. The current baseline includes the project
layout, build/package entry points, planning artifacts, and the first shared contracts.

## Components

- `dpdkd/`: C datapath daemon built with Meson
- `ctrld/`: Python controller package
- `ctl/`: Python CLI package
- `schemas/`: shared contract files
- `docs/`: architecture, workflow, and ticket history

## Current State

Implementation has started with:

- `PLN-001` foundation and build tooling
- `PLN-002` shared contracts and models

For session continuity and progress history, start with [docs/progress.md](docs/progress.md).
