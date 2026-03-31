# pktlab

`pktlab` is a small packet-processing lab with a Python control plane and a C datapath. The
project is being implemented in ticketed slices, and this README is the current reference for how
to build, test, run, and work on the repository as it exists today.

## Status

Implemented today:

- repository skeleton and packaging/build scaffold
- shared IPC and topology contract files
- `pktlab-dpdkd` stub daemon with Unix socket IPC
- datapath smoke test covering framing, success responses, and error responses
- Python datapath IPC framing/helpers, typed Unix-socket client, and controller
  desired/observed/reconcile state models
- controller-side unit/integration coverage for the IPC/state slice

Not implemented yet:

- controller runtime
- CLI runtime
- topology application and teardown
- DPDK EAL, TAP PMD ports, forwarding loop, and rules engine

The current implementation baseline covers `PLN-001` through `PLN-004`. Progress history and the
active ticket live in [docs/progress.md](docs/progress.md).

## README Policy

This file should stay aligned with the real repository state.

- If a change modifies build, test, run, install, or day-to-day developer usage, update this file
  in the same change.
- Do not document planned commands as if they already work.
- Prefer documenting verified entrypoints over aspirational convenience targets.

## Repository Layout

- `dpdkd/`: C datapath daemon, Meson build files, and datapath-side tests
- `ctrld/`: Python controller package scaffold
- `ctl/`: Python CLI package scaffold
- `schemas/`: shared IPC and topology contracts
- `docs/`: roadmap, workflow, tickets, and progress history
- `traffic/`: traffic-generation helpers and future scenario assets
- `lab/`: lab scripts and environment helpers
- `monitoring/`: Prometheus and dashboard assets

## Target Platform

- Ubuntu `24.04.4 LTS`
- Python `3.11+`
- DPDK target version: `25.11.0`

Note: the current datapath stub does not link against DPDK yet. DPDK becomes a runtime/build
dependency in later tickets.

## Prerequisites

Current verified requirements for the implemented slice:

- `python3`
- `meson`
- `ninja`
- a C compiler such as `cc`

Controller-side runtime and tests also depend on the packages declared in `ctrld/pyproject.toml`
and `ctl/pyproject.toml`, notably `pydantic`.

If your Ubuntu host image does not already provide Python packaging tools, install them first:

```sh
sudo apt-get install python3-pip python3-venv
```

Create the project-local virtual environment and install the editable controller and CLI packages:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ctrld -e ctl
```

The root `Makefile` is still scaffold-level. Use the explicit commands below as the authoritative
workflow until later tickets wire the make targets to the real build and test steps.

## Build

Build the current datapath stub:

```sh
meson setup build/dpdkd dpdkd --reconfigure
meson compile -C build/dpdkd
```

Sanity-check the current Python tree:

```sh
.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests ctl/pktlabctl traffic
```

## Test

Run the datapath smoke test directly:

```sh
python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd
```

Run the Meson-driven datapath test suite:

```sh
meson test -C build/dpdkd --print-errorlogs
```

Run the controller test discovery:

```sh
.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v
```

Run the pure state reconcile tests without the controller dependency set:

```sh
python3 -m unittest discover -s ctrld/tests/unit -t ctrld -p 'test_state_reconcile.py' -v
```

Controller test note:

- the full controller suite is verified with the editable packages installed in `.venv`
- the `dpdk_client` integration test exercises the typed IPC client against the C stub daemon

Optional contract sanity checks:

```sh
python3 -c "import json, pathlib; json.loads(pathlib.Path('schemas/dpdkd-ipc.schema.json').read_text())"
python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('schemas/topology.schema.yaml').read_text())"
```

## Run

The only runnable service today is the datapath stub:

```sh
build/dpdkd/pktlab-dpdkd --help
build/dpdkd/pktlab-dpdkd --socket-path /tmp/pktlab-dpdkd.sock
```

Runtime notes:

- default socket path: `/run/pktlab/dpdkd.sock`
- the daemon handles `SIGINT` and `SIGTERM`
- supported IPC commands: `ping`, `get_version`, `get_health`

The Python controller and CLI entrypoints exist only as scaffolding right now and intentionally
exit with a non-zero status:

```sh
python3 -m pktlab_ctrld.main
python3 -m pktlabctl.main
```

## How To Use The Project Today

As a user:

- treat the repo as an implementation baseline, not a complete packet-processing lab yet
- use `pktlab-dpdkd` only as a stub IPC daemon for control-path development and verification
- use the schemas in `schemas/` as the current contract reference

As a developer:

- start with [docs/progress.md](docs/progress.md)
- open the active ticket from [docs/tickets/README.md](docs/tickets/README.md)
- read the latest related commit message when progress history points to it
- inspect only the files relevant to the active ticket before continuing work
- install the editable Python packages before working on controller or CLI code that depends on
  third-party libraries such as `pydantic`

## How To Modify The Project

- update shared contracts first when changing the control-plane/datapath interface
- keep C and Python models aligned with the schema files
- record every meaningful change in [docs/progress.md](docs/progress.md)
- keep commits scoped to one ticket or one coherent sub-slice
- use the structured commit format documented in [docs/workflow.md](docs/workflow.md)
- if your change alters build, test, run, install, or developer workflow, update this README in
  the same change

## Current Next Step

Start `PLN-005`: controller bootstrap, health API, and CLI status.
