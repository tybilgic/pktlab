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
- `pktlab-ctrld` runtime with datapath supervision, FastAPI application bootstrap, and
  `GET /health`
- `pktlabctl status` with human-readable and `--json` output modes
- topology YAML parsing, standalone rules YAML parsing, semantic validation, and
  conservative effective datapath runtime defaults for small machines
- controller- and CLI-side integration coverage for the first end-to-end control slice

Not implemented yet:

- topology application and teardown
- DPDK EAL, TAP PMD ports, forwarding loop, and rules engine

The current implementation baseline covers `PLN-001` through `PLN-006`. Progress history and the
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
.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests ctl/pktlabctl ctl/tests traffic
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

Run the CLI smoke suite:

```sh
.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v
```

Run the pure state reconcile tests without the controller dependency set:

```sh
python3 -m unittest discover -s ctrld/tests/unit -t ctrld -p 'test_state_reconcile.py' -v
```

Controller test note:

- the full controller suite is verified with the editable packages installed in `.venv`
- the `dpdk_client` integration test exercises the typed IPC client against the C stub daemon
- the config unit tests exercise topology/rules parsing, semantic validation, and effective
  datapath runtime derivation

Optional contract sanity checks:

```sh
python3 -c "import json, pathlib; json.loads(pathlib.Path('schemas/dpdkd-ipc.schema.json').read_text())"
python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('schemas/topology.schema.yaml').read_text())"
```

## Run

Build and run the datapath stub directly:

```sh
build/dpdkd/pktlab-dpdkd --help
build/dpdkd/pktlab-dpdkd --socket-path /tmp/pktlab-dpdkd.sock
```

Runtime notes:

- default socket path: `/run/pktlab/dpdkd.sock`
- the daemon handles `SIGINT` and `SIGTERM`
- supported IPC commands: `ping`, `get_version`, `get_health`

Run the controller with datapath supervision:

```sh
.venv/bin/pktlab-ctrld \
  --host 127.0.0.1 \
  --port 8080 \
  --dpdkd-bin build/dpdkd/pktlab-dpdkd \
  --dpdkd-socket-path /tmp/pktlab-dpdkd.sock
```

Query the controller through the CLI:

```sh
.venv/bin/pktlabctl --controller-url http://127.0.0.1:8080 status
.venv/bin/pktlabctl --controller-url http://127.0.0.1:8080 --json status
```

Controller runtime notes:

- controller startup is not considered ready until the supervised datapath answers `ping`,
  `get_health`, and `get_version`
- controller health is exposed at `GET /health`
- `pktlabctl` talks only to the controller HTTP API, not to the datapath socket directly
- local development should usually pass `--dpdkd-socket-path /tmp/...` unless `/run/pktlab/` is
  already provisioned and writable

## How To Use The Project Today

As a user:

- treat the repo as an implementation baseline, not a complete packet-processing lab yet
- use `pktlab-ctrld` plus `pktlabctl status` to exercise the first complete control path
- use `pktlab-dpdkd` directly only when validating datapath-side IPC behavior
- use the schemas in `schemas/` as the current contract reference

As a developer:

- start with [docs/progress.md](docs/progress.md)
- open the active ticket from [docs/tickets/README.md](docs/tickets/README.md)
- read the latest related commit message when progress history points to it
- inspect only the files relevant to the active ticket before continuing work
- install the editable Python packages before working on controller or CLI code that depends on
  third-party libraries such as `pydantic`
- rebuild `build/dpdkd/pktlab-dpdkd` before running controller or CLI integration tests if the C
  stub changed
- use the controller config helpers for direct topology/rules work until a user-facing apply path
  exists:

```python
from pktlab_ctrld.config import (
    load_rules_config,
    load_topology_config,
    validate_ruleset,
    validate_topology_config,
)
```

- the current conservative datapath defaults are `lcores="1"`, `burst_size=32`,
  `rx_queue_size=256`, `tx_queue_size=256`, `mempool_size` derived from port and queue count with
  a minimum of `2048`, and `hugepages_mb` rounded to 2 MB pages with a controller floor of `256`

## How To Modify The Project

- update shared contracts first when changing the control-plane/datapath interface
- keep C and Python models aligned with the schema files
- record every meaningful change in [docs/progress.md](docs/progress.md)
- keep commits scoped to one ticket or one coherent sub-slice
- use the structured commit format documented in [docs/workflow.md](docs/workflow.md)
- if your change alters build, test, run, install, or developer workflow, update this README in
  the same change

## Current Next Step

Start `PLN-007`: topology primitives and TAP reconciliation.
