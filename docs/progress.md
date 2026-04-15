# pktlab Progress Tracker

## Current Focus

- Active milestone: `M4`
- Active ticket: `PLN-008`
- Overall state: `PLN-008` is in progress with real DPDK EAL startup, TAP PMD bring-up, and the single-core forwarding loop verified on a root-capable host; the remaining gap is controller-driven end-to-end traffic verification
- Latest progress entry: `PRG-026`

## Ticket Status

| Ticket | Title | Status | Last Updated | Related Commits | Notes |
| --- | --- | --- | --- | --- | --- |
| PLN-001 | Foundation and Build Tooling | done | 2026-03-31 | `f37b95a` | Repository skeleton, package scaffold, and placeholder non-code assets are in place. |
| PLN-002 | Shared Contracts and Models | done | 2026-03-31 | `02f0283` | Shared IPC/topology schemas and core C/Python type definitions are frozen for the first slice. |
| PLN-003 | Datapath IPC Stub in C | done | 2026-03-31 | `550aa35` | Stub daemon, framing layer, Unix socket server, and smoke test are in place. |
| PLN-004 | Python IPC Client and Controller State | done | 2026-03-31 | `cfcedac`, `a87eb45`, `20af4ba` | Full unit and integration verification completed under the repo virtualenv; next work is `PLN-005`. |
| PLN-005 | Controller Bootstrap, Health API, and CLI Status | done | 2026-04-01 | `012be4d`, `fc08760` | Controller supervision, `/health`, `pktlabctl status`, and integration coverage are in place. |
| PLN-006 | Config Parsing, Validation, and Effective Runtime Policy | done | 2026-04-01 | `e26821b`, `1458a90` | Topology/rules parsing and runtime derivation are in place; standalone rules now report root-relative validation paths while embedded topology rules keep `rules.*` paths. |
| PLN-007 | Topology Primitives and TAP Reconciliation | done | 2026-04-01 | `d83aba1`, `aa59a77`, `1458a90` | Controller-owned topology lifecycle and topology API/CLI commands are in place; destroy now returns the controller to a healthy no-topology steady state. |
| PLN-008 | Datapath EAL, Ports, and Pass-Through Loop | in progress | 2026-04-15 | `4708907`, `e6441db`, `7f7f514`, `d0d29d9`, `d8483bc` | controller-to-daemon runtime plumbing, real DPDK EAL/TAP startup, and the single-core forwarding loop are now in place and the direct root-backed forwarding smoke has passed; the remaining work is controller-driven end-to-end traffic verification |
| PLN-009 | Datapath Status, Stats, and User Surface | not started | 2026-03-31 |  |  |
| PLN-010 | Rules Engine and Atomic Ruleset Replacement | not started | 2026-03-31 |  |  |
| PLN-011 | Capture, Scenarios, and Metrics | not started | 2026-03-31 |  |  |
| PLN-012 | Tests, Packaging, Docs, and Release Polish | not started | 2026-03-31 |  |  |

## Progress Log

Entries are append-only and ordered so session history can be reconstructed without relying on memory.

### PRG-001 | 2026-03-31

- Ticket: planning
- Status change: none -> planning baseline recorded
- Implemented:
  - created the roadmap, workflow, progress tracker, and full ticket set `PLN-001` through `PLN-012`
  - imported the implementation pack into git so the source brief is versioned with the plan
  - initialized the git repository for the project baseline
- Verification:
  - verified the ticket index covers milestones `M1` through `M6`
  - verified the repository was clean after the initial planning commit
- Remaining:
  - convert planning-doc links to relative paths
  - make commit message structure an explicit documented rule
- Risks or blockers:
  - none
- Next step:
  - tighten the docs around link style and commit discipline before implementation starts
- Commit: `febfdb7` `planning: add roadmap, progress tracker, and milestone tickets`

### PRG-002 | 2026-03-31

- Ticket: planning
- Status change: planning baseline recorded -> planning docs normalized
- Implemented:
  - converted internal planning-doc links from absolute workspace paths to relative links
- Verification:
  - scanned `docs/` to confirm there were no remaining `/home/tbilgic/projects/pktlab` path references or absolute markdown links
- Remaining:
  - make commit-message structure a documented project rule
- Risks or blockers:
  - this commit predates the structured commit-message policy, so the rationale lives here in the progress log rather than in the commit body
- Next step:
  - document commit scope and commit message requirements in the workflow and roadmap
- Commit: `1b1c77d` `docs: convert planning links to relative paths`

### PRG-003 | 2026-03-31

- Ticket: planning
- Status change: planning docs normalized -> planning process finalized
- Implemented:
  - made commit scope and structured commit messages mandatory project rules
  - documented required `Why`, `Approach`, and conditional `Tradeoffs` sections for commits
- Verification:
  - reviewed the updated roadmap, workflow, and ticket index
  - verified the repository was clean after the commit
- Remaining:
  - begin implementation with `PLN-001` and `PLN-002`
- Risks or blockers:
  - none
- Next step:
  - start repository scaffolding and shared contract work
- Commit: `dc44e1f` `docs: require structured commit messages for ticket work`

### PRG-004 | 2026-03-31

- Ticket: planning
- Status change: planning process finalized -> planning process verified and ordered
- Implemented:
  - re-reviewed the roadmap, workflow, progress tracker, ticket index, and recent commit messages
  - made the progress tracker explicitly ordered and append-only
  - required all meaningful changes, including planning and documentation updates, to be recorded in the progress log
  - documented that future sessions should read referenced commit messages when additional intent is needed
- Files touched:
  - `docs/roadmap.md`
  - `docs/workflow.md`
  - `docs/tickets/README.md`
  - `docs/progress.md`
- Verification:
  - reviewed the current planning docs for consistency
  - reviewed commit history for `febfdb7`, `1b1c77d`, and `dc44e1f`
  - confirmed the ticket set still covers `PLN-001` through `PLN-012`
- Remaining:
  - commit this progress-ordering and verification update
  - begin implementation with `PLN-001` and `PLN-002`
- Risks or blockers:
  - older commits `febfdb7` and `1b1c77d` predate the structured commit-message rule, so their rationale is preserved here in the ordered progress log
- Next step:
  - create a scoped documentation commit for the ordered progress-log update
- Commit: `f7773dc` `docs: make planning history ordered and implementation-ready`

### PRG-005 | 2026-03-31

- Ticket: PLN-001
- Status change: not started -> done
- Implemented:
  - created the initial repository skeleton, root tooling files, and package metadata for `dpdkd`, `ctrld`, and `ctl`
  - added importable Python package directories and minimal entrypoint scaffolding
  - added placeholder architecture/docs files and non-code lab, traffic, and monitoring assets so the repository shape matches the implementation pack closely
- Files touched:
  - `README.md`
  - `LICENSE`
  - `Makefile`
  - `pyproject.toml`
  - `dpdkd/meson.build`
  - `ctrld/pyproject.toml`
  - `ctl/pyproject.toml`
  - package `__init__.py` and entrypoint scaffold files under `ctrld/` and `ctl/`
  - placeholder files under `docs/`, `traffic/`, `lab/`, and `monitoring/`
- Verification:
  - compared the resulting tree to the implementation-pack layout with `rg --files | sort`
  - confirmed the Python package scaffold compiles with `python3 -m compileall ctrld/pktlab_ctrld ctl/pktlabctl traffic`
- Remaining:
  - no remaining work within `PLN-001`
- Risks or blockers:
  - package entrypoints are intentionally stubbed and will exit until later tickets implement real startup paths
- Next step:
  - complete `PLN-002` by freezing the shared IPC, topology, and core type contracts
- Commit: `f37b95a` `repo: establish the initial pktlab project skeleton`

### PRG-006 | 2026-03-31

- Ticket: PLN-002
- Status change: not started -> done
- Implemented:
  - added the datapath IPC JSON schema covering request, success, and error envelopes plus the required command set
  - added the topology YAML schema covering the base topology objects, embedded ruleset, capture points, and conservative datapath runtime knobs
  - added shared C public headers for datapath types, errors, and version metadata
  - added shared Python models and typed controller-side errors for rules, topology config, and state enums
- Files touched:
  - `schemas/dpdkd-ipc.schema.json`
  - `schemas/topology.schema.yaml`
  - `dpdkd/include/pktlab_dpdkd/types.h`
  - `dpdkd/include/pktlab_dpdkd/errors.h`
  - `dpdkd/include/pktlab_dpdkd/version.h`
  - `ctrld/pktlab_ctrld/types.py`
  - `ctrld/pktlab_ctrld/error.py`
- Verification:
  - validated the IPC schema as JSON with `python3 -c "import json, pathlib; json.loads(pathlib.Path('schemas/dpdkd-ipc.schema.json').read_text())"`
  - validated the topology schema as YAML with `python3 -c "import pathlib; import yaml; yaml.safe_load(pathlib.Path('schemas/topology.schema.yaml').read_text())"`
  - re-ran `python3 -m compileall ctrld/pktlab_ctrld ctl/pktlabctl traffic` after the shared model files were added
- Remaining:
  - no remaining work within `PLN-002`
- Risks or blockers:
  - `get_version` payload fields are intentionally minimal because the brief did not fully specify them; later tickets should extend them only if a concrete requirement appears
- Next step:
  - start `PLN-003` and implement the C IPC framing/helpers and stub datapath socket server against these contracts
- Commit: `02f0283` `contracts: freeze the initial shared schemas and core type definitions`

### PRG-007 | 2026-03-31

- Ticket: PLN-003
- Status change: not started -> done
- Implemented:
  - added the datapath daemon entrypoint, lifecycle wrapper, explicit health/stats/logging modules, and a reusable Unix socket IPC server
  - added bounded JSON frame read/write helpers plus request parsing and success/error response serialization for the current control slice
  - implemented `ping`, `get_version`, and `get_health`, with typed error responses for unknown commands and malformed requests
  - wired Meson to build `pktlab-dpdkd` and added an integration smoke test that exercises framing, success responses, and error responses
- Files touched:
  - `dpdkd/meson.build`
  - `dpdkd/src/main.c`
  - `dpdkd/src/daemon.c`
  - `dpdkd/src/daemon.h`
  - `dpdkd/src/log.c`
  - `dpdkd/src/log.h`
  - `dpdkd/src/health.c`
  - `dpdkd/src/health.h`
  - `dpdkd/src/stats.c`
  - `dpdkd/src/stats.h`
  - `dpdkd/src/json_proto.c`
  - `dpdkd/src/json_proto.h`
  - `dpdkd/src/ipc_server.c`
  - `dpdkd/src/ipc_server.h`
  - `dpdkd/tests/integration/test_ipc_smoke.py`
- Verification:
  - configured the build with `meson setup build/dpdkd dpdkd --reconfigure`
  - compiled the daemon with `meson compile -C build/dpdkd`
  - ran the standalone smoke test with `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd`
  - ran the integrated Meson test with `meson test -C build/dpdkd --print-errorlogs`
- Remaining:
  - no remaining work within `PLN-003`
- Risks or blockers:
  - the default socket path remains `/run/pktlab/dpdkd.sock`, but non-root verification used `--socket-path` to avoid host permission assumptions during local testing
  - JSON handling is intentionally narrow and bounded for the current command set; later tickets should extend it only as the protocol surface grows
- Next step:
  - start `PLN-004` and build the Python datapath client/protocol/state layer against this running C stub
- Commit: `550aa35` `dpdkd: add the IPC stub daemon and smoke test`

### PRG-008 | 2026-03-31

- Ticket: documentation
- Status change: none -> README operational reference added
- Implemented:
  - expanded the root README so it documents the current verified build, test, and run commands instead of only describing the project at a high level
  - documented the current user/developer expectations, including what is implemented today and what is still stubbed
  - made README synchronization an explicit project rule in the workflow, roadmap, and ticket index
- Files touched:
  - `README.md`
  - `docs/workflow.md`
  - `docs/roadmap.md`
  - `docs/tickets/README.md`
- Verification:
  - reviewed the current datapath, Python entrypoints, and build/test configuration before documenting commands
  - checked the updated docs for consistency
  - ran `git diff --check`
- Remaining:
  - continue `PLN-004`
- Risks or blockers:
  - the root `Makefile` remains scaffold-level, so the README intentionally documents direct Meson and Python commands as the current source of truth
- Next step:
  - start implementing the Python IPC protocol, client, and controller state modules for `PLN-004`
- Commit: `3112214` `docs: make the README the current build and usage reference`

### PRG-009 | 2026-03-31

- Ticket: PLN-004
- Status change: not started -> in progress
- Implemented:
  - added Python IPC request/response models, length-prefixed framing helpers, and a typed Unix-socket datapath client for `ping`, `get_version`, and `get_health`
  - added explicit desired state, observed state, and deterministic reconcile-plan models for the controller
  - added controller-side unit and integration tests for the IPC/state slice, with explicit skips when host dependencies such as `pydantic` are unavailable
  - updated the README with controller dependency installation guidance and the new controller test commands
- Files touched:
  - `ctrld/pktlab_ctrld/error.py`
  - `ctrld/pktlab_ctrld/dpdk_client/__init__.py`
  - `ctrld/pktlab_ctrld/dpdk_client/models.py`
  - `ctrld/pktlab_ctrld/dpdk_client/protocol.py`
  - `ctrld/pktlab_ctrld/dpdk_client/client.py`
  - `ctrld/pktlab_ctrld/state/__init__.py`
  - `ctrld/pktlab_ctrld/state/desired.py`
  - `ctrld/pktlab_ctrld/state/observed.py`
  - `ctrld/pktlab_ctrld/state/reconcile.py`
  - `ctrld/tests/__init__.py`
  - `ctrld/tests/unit/__init__.py`
  - `ctrld/tests/integration/__init__.py`
  - `ctrld/tests/unit/test_dpdk_protocol.py`
  - `ctrld/tests/unit/test_dpdk_client.py`
  - `ctrld/tests/unit/test_state_reconcile.py`
  - `ctrld/tests/integration/test_dpdk_client_stub.py`
  - `README.md`
  - `docs/tickets/PLN-004-python-ipc-client-and-controller-state.md`
  - `docs/progress.md`
- Verification:
  - ran `python3 -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `python3 -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `python3 -m unittest discover -s ctrld/tests/unit -t ctrld -p 'test_state_reconcile.py' -v`
  - ran `git diff --check`
- Remaining:
  - install host Python packaging tools and the declared controller dependencies, then rerun the full controller test suite with the `pydantic`-backed IPC/client tests active instead of skipped
- Risks or blockers:
  - the host image does not provide `pip` or `venv`, so I could not install `pydantic` locally to fully exercise the typed datapath client against the C stub daemon
  - `sudo` requires an interactive password in this environment, so I could not self-install the missing host packages
- Next step:
  - either provision `python3-pip` and `python3-venv` on the host or provide an interpreter with `pydantic` available, then finish `PLN-004` verification and proceed to `PLN-005`
- Commit: `cfcedac` `ctrld: add the Python datapath client and controller state layer`

### PRG-010 | 2026-03-31

- Ticket: PLN-004
- Status change: in progress -> done
- Implemented:
  - reran the full controller test suite under the repo virtualenv after the host Python packaging tools and declared dependencies were installed
  - fixed the client integration test cleanup path so the stub daemon `stderr` handle is closed and the verification baseline is warning-free
  - updated the README, progress tracker, and ticket status to reflect that `PLN-004` is now complete and that `PLN-005` is the next active ticket
- Files touched:
  - `ctrld/tests/integration/test_dpdk_client_stub.py`
  - `README.md`
  - `docs/progress.md`
  - `docs/tickets/PLN-004-python-ipc-client-and-controller-state.md`
- Verification:
  - ran `.venv/bin/python -c "import pydantic; print(pydantic.__version__)"`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `git diff --check`
- Remaining:
  - no remaining work within `PLN-004`
- Risks or blockers:
  - none for this ticket
- Next step:
  - start `PLN-005` and wire the controller bootstrap, health API, and CLI status path on top of the now-verified Python IPC/state layer
- Commit: `20af4ba` `pln-004: complete verification of the Python IPC and state slice`

### PRG-011 | 2026-04-01

- Ticket: PLN-005
- Status change: not started -> done
- Implemented:
  - added a datapath supervisor that starts `pktlab-dpdkd`, waits for typed IPC readiness, tracks live process state, and shuts the subprocess down cleanly
  - added the controller runtime, FastAPI app bootstrap, and `GET /health` so the controller now exposes combined controller/datapath health through one API
  - added `pktlabctl status` with human-readable and JSON output modes, backed only by the controller API
  - added controller and CLI integration coverage for the supervised startup path and the end-to-end status command
  - updated the shared test discovery config so the CLI suite is part of the repository test surface
  - updated the README to document the new controller/CLI run and test workflow
- Files touched:
  - `ctrld/pktlab_ctrld/process/supervisor.py`
  - `ctrld/pktlab_ctrld/app.py`
  - `ctrld/pktlab_ctrld/api/app.py`
  - `ctrld/pktlab_ctrld/api/models.py`
  - `ctrld/pktlab_ctrld/api/routes_health.py`
  - `ctrld/pktlab_ctrld/main.py`
  - `ctrld/tests/integration/test_controller_health_api.py`
  - `ctl/pktlabctl/client.py`
  - `ctl/pktlabctl/output.py`
  - `ctl/pktlabctl/commands/status.py`
  - `ctl/pktlabctl/cli.py`
  - `ctl/pktlabctl/main.py`
  - `ctl/tests/__init__.py`
  - `ctl/tests/integration/__init__.py`
  - `ctl/tests/integration/test_status_command.py`
  - `pyproject.toml`
  - `README.md`
  - `docs/tickets/PLN-005-controller-bootstrap-health-api-and-cli-status.md`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests ctl/pktlabctl ctl/tests traffic`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - ran `.venv/bin/pktlab-ctrld --help`
  - ran `.venv/bin/pktlabctl --help`
  - ran `git diff --check`
- Remaining:
  - no remaining work within `PLN-005`
- Risks or blockers:
  - the controller defaults still point at `/run/pktlab/dpdkd.sock`, so local non-root development should continue using an explicit `/tmp/...` socket path until later topology/runtime setup provisions `/run/pktlab/`
- Next step:
  - start `PLN-006` and add topology/rules config parsing plus the conservative effective runtime policy for datapath launch settings
- Commit: `012be4d`, `fc08760`

### PRG-012 | 2026-04-01

- Ticket: PLN-006
- Status change: not started -> done
- Implemented:
  - added controller-side YAML loaders for full topology documents and standalone rules documents
  - added semantic validation for namespaces, links, routes, datapath ports, capture points, and ruleset action targets
  - added conservative effective datapath runtime derivation for `lcores`, queue sizes, mempool sizing, and 2 MB hugepage reservations
  - extended desired and observed state so requested and effective datapath runtime settings can be carried into later topology work
  - added focused unit tests for parser behavior, validation issue aggregation, runtime derivation, and state exposure
- Files touched:
  - `ctrld/pktlab_ctrld/config/__init__.py`
  - `ctrld/pktlab_ctrld/config/topology.py`
  - `ctrld/pktlab_ctrld/config/rules.py`
  - `ctrld/pktlab_ctrld/config/validation.py`
  - `ctrld/pktlab_ctrld/error.py`
  - `ctrld/pktlab_ctrld/state/desired.py`
  - `ctrld/pktlab_ctrld/state/observed.py`
  - `ctrld/pktlab_ctrld/types.py`
  - `ctrld/tests/unit/test_config_topology.py`
  - `ctrld/tests/unit/test_config_rules.py`
  - `ctrld/tests/unit/test_state_reconcile.py`
  - `README.md`
  - `docs/tickets/PLN-006-config-parsing-validation-and-effective-runtime-policy.md`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests/unit -t ctrld -v`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - ran `git diff --check`
- Remaining:
  - no remaining work within `PLN-006`
- Risks or blockers:
  - lcore parsing is intentionally limited to simple list and range syntax for the MVP; full DPDK lcore grammar is deferred until there is a concrete need
  - config validation is currently a controller-internal API only; user-facing topology apply/replace paths arrive in `PLN-007` and later tickets
- Next step:
  - start `PLN-007` and implement namespace, link, route, bridge, and TAP reconciliation primitives on top of the validated desired state
- Commit: `e26821b` `config: add topology and rules validation with conservative runtime defaults`

### PRG-013 | 2026-04-01

- Ticket: PLN-007
- Status change: not started -> done
- Implemented:
  - added centralized subprocess, netns, and timeout helpers for controller-owned topology mutations
  - added namespace, link, bridge, route, and TAP reconciliation modules plus a serialized topology manager
  - extended the controller runtime and supervisor so topology apply restarts `pktlab-dpdkd` in the datapath namespace and tracks topology state
  - added controller routes and CLI commands for topology apply/destroy while preserving the `pktlabctl -> pktlab-ctrld` boundary
  - added fake-system integration coverage for topology orchestration plus API and CLI smoke tests for the new surface
- Files touched:
  - `ctrld/pktlab_ctrld/error.py`
  - `ctrld/pktlab_ctrld/config/validation.py`
  - `ctrld/pktlab_ctrld/process/supervisor.py`
  - `ctrld/pktlab_ctrld/app.py`
  - `ctrld/pktlab_ctrld/util/__init__.py`
  - `ctrld/pktlab_ctrld/util/subprocess.py`
  - `ctrld/pktlab_ctrld/util/netns.py`
  - `ctrld/pktlab_ctrld/util/time.py`
  - `ctrld/pktlab_ctrld/topology/__init__.py`
  - `ctrld/pktlab_ctrld/topology/namespaces.py`
  - `ctrld/pktlab_ctrld/topology/links.py`
  - `ctrld/pktlab_ctrld/topology/routes.py`
  - `ctrld/pktlab_ctrld/topology/taps.py`
  - `ctrld/pktlab_ctrld/topology/manager.py`
  - `ctrld/pktlab_ctrld/api/app.py`
  - `ctrld/pktlab_ctrld/api/models.py`
  - `ctrld/pktlab_ctrld/api/routes_topology.py`
  - `ctrld/tests/integration/test_topology_manager.py`
  - `ctrld/tests/integration/test_topology_api.py`
  - `ctl/pktlabctl/cli.py`
  - `ctl/pktlabctl/client.py`
  - `ctl/pktlabctl/output.py`
  - `ctl/pktlabctl/commands/topology.py`
  - `ctl/tests/integration/test_topology_command.py`
  - `README.md`
  - `docs/tickets/PLN-007-topology-primitives-and-tap-reconciliation.md`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests ctl/pktlabctl ctl/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - ran `git diff --check`
- Remaining:
  - no remaining work within `PLN-007`
- Risks or blockers:
  - topology tests use a fake netns system rather than live privileged namespace mutations, so a real root-backed smoke test is still deferred to later operational hardening
  - the bridge-side mapping is currently fixed to `veth-in-k` and `veth-out-k` because the topology schema does not yet expose an explicit ingress/egress bridge attachment map
- Next step:
  - start `PLN-008` and implement the real datapath EAL init, TAP PMD ports, and pass-through forwarding loop
- Commit: `d83aba1` `topology: add controller-owned topology primitives and orchestration`; `aa59a77` `api: add topology apply and destroy routes plus CLI commands`

### PRG-014 | 2026-04-01

- Ticket: `PLN-006`, `PLN-007`
- Status change: done -> done with verification follow-up fixes
- Implemented:
  - fixed controller health recomputation so `destroy_topology()` settles to `running` when no datapath is desired and only degrades if a datapath remains unexpectedly active
  - fixed standalone rules validation paths so standalone files report `default_action.*` and `entries[*].*`, while embedded topology rules continue to report `rules.*`
  - added controller-runtime regression coverage for the post-destroy steady state and the unexpected-running-datapath state
  - clarified the README so the topology API/CLI surface is documented as implemented, while live TAP-backed apply remains deferred until `PLN-008`
- Files touched:
  - `ctrld/pktlab_ctrld/app.py`
  - `ctrld/pktlab_ctrld/config/validation.py`
  - `ctrld/tests/unit/test_controller_runtime.py`
  - `ctrld/tests/unit/test_config_rules.py`
  - `ctrld/tests/unit/test_config_topology.py`
  - `README.md`
  - `docs/tickets/PLN-006-config-parsing-validation-and-effective-runtime-policy.md`
  - `docs/tickets/PLN-007-topology-primitives-and-tap-reconciliation.md`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests/unit -t ctrld -p 'test_controller_runtime.py' -v`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests/unit -t ctrld -p 'test_config_rules.py' -v`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests/unit -t ctrld -p 'test_config_topology.py' -v`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - ran `git diff --check`
- Remaining:
  - no remaining follow-up work is known for `PLN-006` or `PLN-007`
- Risks or blockers:
  - live topology apply is still expected to fail against the current datapath stub because `dtap0` and `dtap1` are not created until `PLN-008`
- Next step:
  - resume `PLN-008` and implement the real datapath EAL init, TAP PMD ports, and pass-through forwarding loop
- Commit:
  - `1458a90` `ctrld: fix destroy-state health and standalone rules paths`
  - `9d070f0` `docs: sync README and history for PLN-006 and PLN-007 fixes`

### PRG-015 | 2026-04-02

- Ticket: `PLN-006`, `PLN-007`, pre-`PLN-008` hardening review
- Status change: `PLN-008` ready to start -> hardening fixes required before `PLN-008`
- Implemented:
  - reviewed the implemented controller, CLI, datapath stub, schemas, and docs against the current roadmap and progress log
  - reran the current build and test suites for `dpdkd`, `ctrld`, and `ctl`
  - reproduced the remaining controller state-management and topology-manager edge cases with targeted runtime probes
  - recorded the verification results and the recommended hardening order in this progress log
- Files touched:
  - `docs/progress.md`
- Verification:
  - ran `meson compile -C build/dpdkd`
  - ran `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd`
  - ran `meson test -C build/dpdkd --print-errorlogs`
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests ctl/pktlabctl ctl/tests traffic`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `.venv/bin/python -m unittest discover -s ctl/tests -t ctl -v`
  - ran targeted `.venv/bin/python -c` reproductions to confirm stale state after failed apply, same-path no-op reapply, and destroy-without-topology behavior
- Remaining:
  - `ControllerRuntime.apply_topology()` leaves stale `desired_state` and `observed_state` after failures, so `/health` can report misleading topology state and overwrite the original error
  - `ControllerRuntime.destroy_topology()` is still not idempotent when no topology is applied but the datapath remains running
  - `TopologyManager.apply()` short-circuits on config-path equality, which blocks same-path reapply and reports a misleading `datapath_running=True`
  - failed apply rollback currently swallows cleanup errors, which can hide partially torn down topology state
  - the IPC, rules, README/sample topology, and OpenAPI docs still drift from the actual implementation in a few places
  - topology coverage still relies on fake netns and HTTP stubs rather than live privileged apply/destroy verification
- Risks or blockers:
  - the current test suites pass, but they do not cover the failing controller invariants or real-system topology behavior that the review exposed
  - live topology apply is still expected to fail against the datapath stub until `PLN-008` creates `dtap0` and `dtap1`
- Recommendations:
  - fix the apply/destroy state invariants first and add regression tests around those paths
  - remove the same-path apply shortcut and surface rollback cleanup failures to the caller
  - align the shared contracts, placeholder docs, and sample assets with what is actually implemented today
  - add at least one real root-backed topology smoke path before treating topology orchestration as hardened
  - resume `PLN-008` only after those control-plane fixes are merged
- Next step:
  - implement the controller/topology hardening fixes and regression coverage from this review before resuming datapath feature work
- Commit:
  - `885e865` `ctrld: harden topology state and rollback handling`

### PRG-016 | 2026-04-02

- Ticket: pre-`PLN-008` hardening follow-up
- Status change: hardening fixes required before `PLN-008` -> core controller/topology hardening fixes landed; a few pre-`PLN-008` follow-ups still remain
- Implemented:
  - fixed `ControllerRuntime.apply_topology()` so failed apply clears stale no-longer-valid topology state when no topology remains active and preserves the original failure message across later `/health` reads
  - fixed `ControllerRuntime.destroy_topology()` so destroy returns the controller to a healthy no-topology steady state even when the topology manager reports that nothing is currently applied but the supervised datapath is still running
  - removed the config-path equality shortcut from `TopologyManager.apply()` so same-path apply performs a real reconcile instead of a misleading no-op
  - surfaced rollback cleanup failures from failed apply attempts by attaching cleanup error details to the raised topology/apply error
  - added regression coverage for the controller runtime and topology manager around the reproduced hardening bugs
  - aligned the IPC schema required fields with the Python client models and replaced the placeholder `lab/topologies/linear.yaml` with a valid sample topology referenced by the README
- Files touched:
  - `ctrld/pktlab_ctrld/app.py`
  - `ctrld/pktlab_ctrld/topology/manager.py`
  - `ctrld/tests/unit/test_controller_runtime.py`
  - `ctrld/tests/integration/test_topology_manager.py`
  - `schemas/dpdkd-ipc.schema.json`
  - `lab/topologies/linear.yaml`
  - `README.md`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `.venv/bin/python -c "from pktlab_ctrld.config.topology import load_topology_config; from pktlab_ctrld.config.validation import validate_topology_config; validate_topology_config(load_topology_config('lab/topologies/linear.yaml')); print('validated')"`
  - ran `git diff --check`
- Remaining:
  - `schemas/rules.schema.yaml` is still a placeholder even though standalone rules parsing/validation exists
  - `schemas/ctrld-api.openapi.yaml` is still a placeholder and does not yet document the implemented controller API surface
  - topology orchestration coverage is still fake-netns and stub-based; there is still no root-backed apply/destroy smoke path
  - live topology apply is still expected to fail against the current datapath stub until `PLN-008` creates `dtap0` and `dtap1`
- Risks or blockers:
  - the controller and topology-manager invariants are now covered by tests, but the remaining real-system topology smoke gap means privileged host behavior is still not proven end to end
- Next step:
  - decide whether to finish the remaining doc/schema cleanup and add a real privileged topology smoke path before resuming `PLN-008`
- Commit:
  - `885e865` `ctrld: harden topology state and rollback handling`

### PRG-017 | 2026-04-02

- Ticket: pre-`PLN-008` hardening follow-up
- Status change: pre-`PLN-008` follow-ups include placeholder docs/contracts plus privileged topology smoke coverage -> placeholder docs/contracts replaced; privileged topology smoke coverage remains
- Implemented:
  - replaced the placeholder standalone rules schema with the structural contract that matches `RulesetModel`, including rule match/action fields and action-specific `port` requirements
  - replaced the placeholder controller OpenAPI file with the currently implemented HTTP surface for `GET /health`, `POST /topology/apply`, and `POST /topology/destroy`
  - documented both FastAPI request-shape validation failures and the controller's custom `PktlabError` response envelope so the checked-in API contract matches real route behavior rather than the placeholder
- Files touched:
  - `schemas/rules.schema.yaml`
  - `schemas/ctrld-api.openapi.yaml`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('schemas/rules.schema.yaml').read_text()); yaml.safe_load(pathlib.Path('schemas/ctrld-api.openapi.yaml').read_text()); print('schema docs parse')"`
  - ran `.venv/bin/python -c "from pktlab_ctrld.api.app import create_api_app; app = create_api_app(type('ControllerStub', (), {})()); paths = sorted(app.openapi()['paths']); assert paths == ['/health', '/topology/apply', '/topology/destroy']; print('openapi paths verified')"`
  - ran `git diff --check`
- Remaining:
  - topology orchestration coverage is still fake-netns and stub-based; there is still no root-backed apply/destroy smoke path
  - live topology apply is still expected to fail against the current datapath stub until `PLN-008` creates `dtap0` and `dtap1`
- Risks or blockers:
  - the checked-in contract docs now match the implemented rules/API surface, but privileged host behavior is still not proven end to end
- Next step:
  - add a real privileged topology apply/destroy smoke path, then resume `PLN-008`
- Commit:
  - `dcc980d` `docs: replace placeholder rules and controller API contracts`

### PRG-018 | 2026-04-14

- Ticket: pre-`PLN-008` hardening follow-up
- Status change: privileged topology smoke coverage missing -> privileged topology smoke path added and documented for root-capable hosts
- Implemented:
  - added an opt-in integration smoke test that drives `TopologyManager` through the real `ip netns` helper instead of the fake in-memory netns runner
  - made the privileged smoke test create synthetic datapath-side `dtap0` and `dtap1` interfaces in the datapath namespace so the host-side apply/destroy path can be verified before `PLN-008` lands the real TAP-backed datapath
  - documented the explicit privileged smoke command in the README and clarified that the default controller suite still uses the fake-netns topology integration coverage while the new smoke path is opt-in
- Files touched:
  - `ctrld/tests/integration/test_topology_manager_privileged.py`
  - `README.md`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - confirmed the new privileged smoke test is present in controller test discovery and cleanly skips without `PKTLAB_RUN_PRIVILEGED_TOPOLOGY_SMOKE=1` in this non-root environment
- Remaining:
  - run `sudo env PKTLAB_RUN_PRIVILEGED_TOPOLOGY_SMOKE=1 .venv/bin/python -m unittest discover -s ctrld/tests/integration -t ctrld -p 'test_topology_manager_privileged.py' -v` on a root-capable host to verify the new real-host path end to end
  - live topology apply is still expected to fail against the current datapath stub until `PLN-008` creates `dtap0` and `dtap1`
- Risks or blockers:
  - the repo now contains the missing privileged topology smoke coverage, but this environment cannot execute it because the current user is not root and does not have `CAP_NET_ADMIN`
- Next step:
  - run the privileged topology smoke path on a root-capable host, then start `PLN-008`
- Commit:
  - `e950097` `tests: add a privileged topology smoke path`

### PRG-019 | 2026-04-14

- Ticket: pre-`PLN-008` hardening follow-up
- Status change: privileged topology smoke path added -> first root-backed smoke run exposed a real route-ordering defect; fix landed in repo and the smoke path should be rerun
- Implemented:
  - analyzed the first real privileged smoke failure and confirmed that `TopologyManager.apply()` was programming static routes before the topology links were brought up
  - moved route installation to the end of the apply flow so host-facing interfaces and datapath-side bridge attachments are already up before static routes are installed
  - strengthened the fake-netns topology-manager integration test so it asserts route programming happens after the relevant source and sink interfaces are brought up
- Files touched:
  - `ctrld/pktlab_ctrld/topology/manager.py`
  - `ctrld/tests/integration/test_topology_manager.py`
  - `docs/progress.md`
- Verification:
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -p 'test_topology_manager.py' -v`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `git diff --check`
- Remaining:
  - rerun `sudo env PKTLAB_RUN_PRIVILEGED_TOPOLOGY_SMOKE=1 .venv/bin/python -m unittest discover -s ctrld/tests/integration -t ctrld -p 'test_topology_manager_privileged.py' -v` on a root-capable host to confirm the real host-backed path now passes
  - live topology apply is still expected to fail against the current datapath stub until `PLN-008` creates `dtap0` and `dtap1`
- Risks or blockers:
  - this environment still cannot execute the privileged host-backed smoke path because the current user is not root and does not have `CAP_NET_ADMIN`
- Next step:
  - rerun the privileged topology smoke path on a root-capable host and, if it passes, resume `PLN-008`
- Commit:
  - `e5d17ed` `topology: install static routes after links are up`

### PRG-020 | 2026-04-14

- Ticket: pre-`PLN-008` hardening follow-up
- Status change: route-ordering fix landed and waiting for root-backed confirmation -> privileged topology smoke path passed on a root-capable host; pre-`PLN-008` hardening is complete
- Implemented:
  - executed the opt-in privileged topology smoke test on a root-capable host
  - verified that the real `ip netns` apply/destroy path now completes successfully end to end after the route-ordering fix
  - updated the tracker so `PLN-008` is explicitly ready to resume
- Files touched:
  - `docs/progress.md`
- Verification:
  - ran `sudo env PKTLAB_RUN_PRIVILEGED_TOPOLOGY_SMOKE=1 .venv/bin/python -m unittest discover -s ctrld/tests/integration -t ctrld -p 'test_topology_manager_privileged.py' -v`
  - confirmed `test_apply_and_destroy_mutate_the_real_host_network_stack` passed
- Remaining:
  - start `PLN-008` and implement the real datapath EAL init, TAP PMD ports, and pass-through forwarding loop
- Risks or blockers:
  - live topology apply against the real datapath remains blocked until `PLN-008` creates `dtap0` and `dtap1`; this is now the intended next implementation step rather than a hardening blocker
- Next step:
  - start `PLN-008`
- Commit:
  - `203c082` `docs: record successful privileged topology smoke verification`

### PRG-021 | 2026-04-14

- Ticket: `PLN-008`
- Status change: not started -> in progress
- Implemented:
  - added controller-side rendering of the validated datapath runtime profile into `pktlab-dpdkd`
    launch arguments for `lcores`, `hugepages_mb`, queue sizes, mempool size, and deterministic
    ingress/egress TAP names
  - extended `pktlab-dpdkd` CLI parsing and daemon config so those runtime knobs are accepted and
    validated at startup
  - added the first `PLN-008` datapath module scaffolding in `dpdkd/src/datapath.c`,
    `dpdkd/src/eal.c`, and `dpdkd/src/ports.c`
  - taught Meson to look for `libdpdk.pc` and compile an honest fallback build when the
    development package is absent, instead of pretending the fast path exists
  - updated the datapath smoke test to exercise the new runtime-argument surface
- Files touched:
  - `ctrld/pktlab_ctrld/app.py`
  - `ctrld/tests/unit/test_controller_runtime.py`
  - `dpdkd/meson.build`
  - `dpdkd/src/daemon.c`
  - `dpdkd/src/daemon.h`
  - `dpdkd/src/main.c`
  - `dpdkd/src/datapath.c`
  - `dpdkd/src/datapath.h`
  - `dpdkd/src/eal.c`
  - `dpdkd/src/eal.h`
  - `dpdkd/src/ports.c`
  - `dpdkd/src/ports.h`
  - `dpdkd/tests/integration/test_ipc_smoke.py`
  - `README.md`
  - `docs/progress.md`
- Verification:
  - confirmed `meson setup build/dpdkd dpdkd --reconfigure` resolved `libdpdk` `25.11.0` on this host
  - reconfigured and rebuilt `dpdkd` with `meson setup build/dpdkd dpdkd --reconfigure` and
    `meson compile -C build/dpdkd`
  - ran `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd`
  - ran `meson test -C build/dpdkd --print-errorlogs`
  - ran `.venv/bin/python -m compileall ctrld/pktlab_ctrld ctrld/tests`
  - ran `.venv/bin/python -m unittest discover -s ctrld/tests -t ctrld -v`
  - ran `git diff --check`
- Remaining:
  - replace the fallback datapath start path with real `rte_eal_init()` and TAP PMD bring-up
  - create `dtap0` and `dtap1` from DPDK so controller TAP reconciliation can succeed live
  - add the single-core pass-through forwarding loop and verify packets cross the lab
- Risks or blockers:
  - the DPDK toolchain is present on this host, so the remaining gap is implementation rather than
    dependency discovery; the real EAL path still needs a follow-up slice and runtime verification
- Next step:
  - implement the actual DPDK EAL startup and TAP PMD device creation inside the new datapath
    module layout
- Commit:
  - `76cb42d` `dpdkd: add PLN-008 runtime plumbing and module scaffolding`

### PRG-022 | 2026-04-15

- Ticket: `PLN-008`
- Status change: runtime plumbing and module scaffolding in place -> real DPDK EAL startup and TAP PMD bring-up implemented
- Implemented:
  - replaced the placeholder datapath start path with real DPDK EAL initialization when `libdpdk`
    is available and the daemon is running with root or `CAP_NET_ADMIN`
  - added TAP PMD port discovery, mbuf pool creation, queue configuration, and device start/cleanup
    for deterministic ingress and egress TAP names
  - made datapath health honest across environments: `running` with `ports_ready=true` when the
    fast path is up, and `degraded` with `ports_ready=false` when the daemon is unprivileged or
    built without `libdpdk`
  - updated the default IPC smoke test to validate the new startup semantics instead of the old
    stub-era always-running expectation
  - added an opt-in privileged datapath smoke script for real TAP startup verification on a
    root-capable host
- Files touched:
  - `dpdkd/src/daemon.c`
  - `dpdkd/src/datapath.c`
  - `dpdkd/src/datapath.h`
  - `dpdkd/src/eal.c`
  - `dpdkd/src/eal.h`
  - `dpdkd/src/ports.c`
  - `dpdkd/src/ports.h`
  - `dpdkd/tests/integration/test_ipc_smoke.py`
  - `dpdkd/tests/integration/test_tap_startup_privileged.py`
  - `README.md`
  - `docs/tickets/PLN-008-datapath-eal-ports-and-pass-through-loop.md`
  - `docs/progress.md`
- Verification:
  - rebuilt `dpdkd` with `meson compile -C build/dpdkd`
  - ran `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd`
  - ran `meson test -C build/dpdkd --print-errorlogs`
  - verified the live non-root health payload reports `degraded` with `ports_ready=false` and the
    expected TAP naming context
- Remaining:
  - add the single-core pass-through forwarding loop so packets actually traverse ingress -> egress
  - verify the new privileged datapath TAP-startup smoke on a root-capable host
  - run a real controller-driven topology apply/traffic smoke against the TAP-backed datapath
- Risks or blockers:
  - this environment is not root-capable, so the new privileged TAP-startup smoke could not be
    executed here
  - live packet forwarding is still absent; topology reconciliation can now bind the TAP devices,
    but packet movement is still blocked on the forwarding loop
- Next step:
  - implement the single-core pass-through datapath loop, then verify the privileged startup and
    controller-driven traffic path end to end
- Commit:
  - `4708907` `dpdkd: add EAL startup and TAP PMD configuration`

### PRG-023 | 2026-04-15

- Ticket: `PLN-008`
- Status change: real DPDK EAL startup and TAP PMD bring-up implemented -> first root-backed TAP-startup smoke exposed an invalid EAL argv combination; fix landed and the smoke should be rerun
- Implemented:
  - investigated the privileged TAP-startup smoke failure and confirmed that `rte_eal_init()` rejects the specific `--in-memory` plus `--huge-unlink=always` combination used by the new datapath startup path
  - removed the incompatible `--huge-unlink=always` flag from the generated DPDK EAL argv while keeping the intended in-memory single-process startup profile
  - factored DPDK argv rendering into a shared helper so the startup shape is inspectable and testable without needing privileged execution
  - added a new `dpdkd` unit test that asserts the generated argv keeps `--in-memory`, retains the deterministic TAP `--vdev` arguments, and does not reintroduce the incompatible `--huge-unlink=always` flag
- Files touched:
  - `dpdkd/src/eal.c`
  - `dpdkd/src/eal.h`
  - `dpdkd/tests/unit/test_eal_args.c`
  - `dpdkd/meson.build`
  - `docs/progress.md`
- Verification:
  - rebuilt `dpdkd` with `meson compile -C build/dpdkd`
  - ran `meson test -C build/dpdkd --print-errorlogs`
  - reran `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd`
  - ran `git diff --check`
- Remaining:
  - rerun `sudo env PKTLAB_RUN_PRIVILEGED_DPDKD_SMOKE=1 python3 dpdkd/tests/integration/test_tap_startup_privileged.py build/dpdkd/pktlab-dpdkd` on a root-capable host to confirm the EAL startup fix against the real host network stack
  - add the single-core pass-through forwarding loop so packets actually traverse ingress -> egress
  - run a real controller-driven topology apply plus source -> datapath -> sink traffic smoke once forwarding exists
- Risks or blockers:
  - this environment still cannot execute the privileged datapath smoke path, so the final confirmation for the EAL argument fix depends on a rerun on the root-capable host
  - the specific argv incompatibility is now covered by a unit test, but further privileged runtime issues may still appear once the TAP-startup smoke advances past EAL initialization
- Next step:
  - rerun the privileged datapath TAP-startup smoke on the root-capable host and, if it passes, move on to the single-core forwarding loop
- Commit:
  - `e6441db` `dpdkd: fix the privileged EAL startup arguments`

### PRG-024 | 2026-04-15

- Ticket: `PLN-008`
- Status change: privileged EAL argv incompatibility fixed -> privileged TAP-startup smoke now provisions the minimum hugepages it needs before launching the daemon
- Implemented:
  - investigated the next root-backed TAP-startup smoke failure and confirmed that the host had zero free 2 MB hugepages, so DPDK aborted during EAL initialization before TAP creation
  - updated the privileged datapath smoke script to reserve the minimum 2 MB hugepages required by the configured `--hugepages-mb` budget before starting `pktlab-dpdkd`
  - made the smoke restore the original host hugepage total after the daemon exits so the verification remains self-contained instead of leaving kernel hugepage state behind
  - clarified in the README that the privileged datapath smoke now manages its temporary hugepage reservation, while normal root-backed datapath runs still require the requested hugepage budget to be available
- Files touched:
  - `dpdkd/tests/integration/test_tap_startup_privileged.py`
  - `README.md`
  - `docs/progress.md`
- Verification:
  - ran `python3 -m compileall dpdkd/tests`
  - ran `python3 dpdkd/tests/integration/test_tap_startup_privileged.py build/dpdkd/pktlab-dpdkd` and confirmed it still cleanly skips without `PKTLAB_RUN_PRIVILEGED_DPDKD_SMOKE=1` in this non-root environment
  - ran `git diff --check`
- Remaining:
  - rerun `sudo env PKTLAB_RUN_PRIVILEGED_DPDKD_SMOKE=1 python3 dpdkd/tests/integration/test_tap_startup_privileged.py build/dpdkd/pktlab-dpdkd` on the root-capable host to confirm the hugepage-managed smoke now completes end to end
  - add the single-core pass-through forwarding loop so packets actually traverse ingress -> egress
  - run a real controller-driven topology apply plus source -> datapath -> sink traffic smoke once forwarding exists
- Risks or blockers:
  - this environment still cannot execute the privileged datapath smoke path, so the final confirmation for the hugepage-handling change depends on a rerun on the root-capable host
  - the smoke now provisions only the minimum hugepages needed for its own run; normal controller-driven or manual datapath runs still need explicit hugepage availability on the host
- Next step:
  - rerun the privileged datapath TAP-startup smoke on the root-capable host and, if it passes, move on to the single-core forwarding loop
- Commit:
  - `7f7f514` `tests: provision hugepages for the privileged datapath smoke`

### PRG-025 | 2026-04-15

- Ticket: `PLN-008`
- Status change: privileged TAP-startup smoke now self-provisions its minimum hugepages before launch -> privileged TAP-startup smoke passed on a root-capable host with explicit success output
- Implemented:
  - updated the `dpdkd` smoke scripts so successful runs print an explicit `ok:` line instead of exiting silently
  - kept the existing `skipping:` output and exception-driven failure paths unchanged so success, skip, and failure remain distinguishable at the terminal
  - confirmed on a root-capable host that the privileged TAP-startup smoke now completes end to end and reports `ok: privileged datapath TAP startup smoke passed`
- Files touched:
  - `dpdkd/tests/integration/test_ipc_smoke.py`
  - `dpdkd/tests/integration/test_tap_startup_privileged.py`
  - `docs/progress.md`
- Verification:
  - ran `python3 -m compileall dpdkd/tests`
  - ran `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd` and confirmed it now prints an explicit success line in the local non-root path
  - ran `python3 dpdkd/tests/integration/test_tap_startup_privileged.py build/dpdkd/pktlab-dpdkd` in this environment and confirmed it still prints a clear `skipping:` message when the privileged opt-in env var is absent
  - reran `sudo env PKTLAB_RUN_PRIVILEGED_DPDKD_SMOKE=1 python3 dpdkd/tests/integration/test_tap_startup_privileged.py build/dpdkd/pktlab-dpdkd` on the root-capable host and confirmed it completed with `ok: privileged datapath TAP startup smoke passed`
- Remaining:
  - add the single-core pass-through forwarding loop so packets actually traverse ingress -> egress
  - run a real controller-driven topology apply plus source -> datapath -> sink traffic smoke once forwarding exists
- Risks or blockers:
  - datapath startup and TAP creation are now verified, but there is still no packet-processing loop, so live traffic cannot traverse the datapath yet
  - the privileged smoke manages hugepages for its own run; controller-driven or manual datapath runs still need the configured hugepage budget available on the host
- Next step:
  - implement the single-core forwarding loop in `pktlab-dpdkd`, then run a real controller-driven source -> datapath -> sink traffic smoke
- Commit:
  - `d0d29d9` `tests: print explicit success output for smoke scripts`

### PRG-026 | 2026-04-15

- Ticket: `PLN-008`
- Status change: privileged TAP-startup smoke passed on a root-capable host with explicit success output -> single-core forwarding loop implemented and direct privileged forwarding smoke verified on a root-capable host
- Implemented:
  - added the missing datapath packet-path modules in `dpdkd/src/parser.c` and `dpdkd/src/actions.c` so the forwarding loop has bounded header parsing and explicit burst-forward/drop helpers instead of embedding everything in one file
  - implemented a bidirectional single-core pass-through loop in `dpdkd/src/datapath.c` that polls ingress and egress TAP PMD ports, drops malformed packets, forwards valid bursts to the opposite side, and keeps internal packet/drop counters for the next status-surface ticket
  - aligned the C-side burst-size validation with the controller's existing MVP ceiling so the hot path can stay allocation-free inside the loop
  - added an opt-in privileged forwarding smoke script that stands up root-backed source and sink namespaces around `dtap0` and `dtap1` and pings across the real datapath fast path
  - updated the README to document the forwarding slice and the new privileged smoke entrypoint
- Files touched:
  - `dpdkd/meson.build`
  - `dpdkd/src/datapath.c`
  - `dpdkd/src/datapath.h`
  - `dpdkd/src/ports.c`
  - `dpdkd/src/parser.c`
  - `dpdkd/src/parser.h`
  - `dpdkd/src/actions.c`
  - `dpdkd/src/actions.h`
  - `dpdkd/tests/integration/test_forwarding_privileged.py`
  - `README.md`
  - `docs/progress.md`
- Verification:
  - rebuilt `dpdkd` with `meson compile -C build/dpdkd`
  - ran `meson test -C build/dpdkd --print-errorlogs`
  - reran `python3 dpdkd/tests/integration/test_ipc_smoke.py build/dpdkd/pktlab-dpdkd`
  - ran `python3 -m compileall dpdkd/tests`
  - ran `python3 dpdkd/tests/integration/test_forwarding_privileged.py build/dpdkd/pktlab-dpdkd` and confirmed it cleanly reports `skipping:` without the privileged opt-in env var
  - reran `sudo env PKTLAB_RUN_PRIVILEGED_DPDKD_FORWARDING_SMOKE=1 python3 dpdkd/tests/integration/test_forwarding_privileged.py build/dpdkd/pktlab-dpdkd` on a root-capable host and confirmed it completed with `ok: privileged datapath forwarding smoke passed`
- Remaining:
  - run a real controller-driven topology apply plus source -> datapath -> sink traffic smoke now that the direct datapath forwarding path exists
- Risks or blockers:
  - the current checked-in `lab/topologies/linear.yaml` remains a routed topology sample, while the new direct forwarding smoke intentionally uses a simpler same-subnet bridge layout to exercise the pass-through loop itself rather than a later routing story
- Next step:
  - wire and verify a real controller-driven topology apply plus source -> datapath -> sink traffic smoke
- Commit:
  - `d8483bc` `dpdkd: add the single-core pass-through forwarding loop`

## Read Before Continuing

- Start with the latest progress entry and work backward only as needed.
- Read the commit message for any referenced commit when additional intent is needed.
- If the referenced commit predates the structured commit format, use the progress entry as the explanatory source of truth.

## Update Template

Copy this block when updating the progress log:

```text
### PRG-XXX | YYYY-MM-DD

- Ticket: PLN-XXX
- Status change: <from> -> <to>
- Implemented:
- Files touched:
- Verification:
- Remaining:
- Risks or blockers:
- Next step:
- Commit:
```
