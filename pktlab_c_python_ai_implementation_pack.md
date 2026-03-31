# pktlab C + Python Implementation Pack

## Purpose

This document is the machine-oriented implementation pack for **pktlab**, adapted to use:

- **C** for `pktlab-dpdkd`
- **Python** for `pktlab-ctrld`
- **Python** for `pktlabctl`

It is written for two audiences at the same time:

1. Humans designing and reviewing the system
2. AI coding assistants implementing modules with minimal ambiguity

The goal is to reduce architecture drift, avoid accidental coupling, and make generated code more accurate.

---

# 1. Project Summary

## 1.1 What pktlab is

`pktlab` is a single-host, namespace-based packet processing lab for experimenting with DPDK-based packet processing in a reproducible and observable environment.

The system must:

- run on one Linux machine
- not require hardware NIC passthrough
- use Linux namespaces and kernel-visible links for observability
- run a DPDK datapath daemon in the middle
- expose a controller API and CLI
- support packet generation, capture, telemetry, and rule updates
- be easy to tear down and re-create
- be easy to extend

## 1.2 Language split

- `pktlab-dpdkd`: **C**
- `pktlab-ctrld`: **Python**
- `pktlabctl`: **Python**

## 1.3 Why Python instead of Rust

Python is selected for the controller and CLI because:

- faster iteration for orchestration-heavy code
- easier integration with subprocesses, sockets, YAML, HTTP, and Linux tools
- easy readability for operators and contributors
- lower friction for AI coding assistants generating infrastructure code

This choice is acceptable because:

- control-plane throughput requirements are low
- datapath remains in C where performance matters
- process boundaries prevent Python from contaminating the packet fast path

---

# 2. Process Model

## 2.1 Processes

### `pktlab-dpdkd`
Language: C

Responsibilities:
- initialize DPDK
- own ports and packet processing
- own active datapath rule set
- maintain datapath counters
- expose a local IPC socket
- report health/status/version

### `pktlab-ctrld`
Language: Python

Responsibilities:
- parse topology and rule config
- validate config
- create and destroy namespaces and links
- supervise `pktlab-dpdkd`
- reconcile desired and observed state
- expose external API
- expose Prometheus metrics
- manage captures and scenarios
- aggregate system state for humans and tools

### `pktlabctl`
Language: Python

Responsibilities:
- provide human and script friendly CLI
- talk only to `pktlab-ctrld`
- never talk directly to `pktlab-dpdkd` in normal operation

## 2.2 Control hierarchy

The control hierarchy is:

```text
pktlabctl -> pktlab-ctrld -> pktlab-dpdkd
```

This must remain true.

---

# 3. Repository Layout

```text
pktlab/
  README.md
  LICENSE
  Makefile
  pyproject.toml
  .gitignore

  docs/
    architecture.md
    process-model.md
    topology.md
    ipc.md
    datapath.md
    controller.md
    observability.md
    coding-rules.md
    ai-assistant-instructions.md

  schemas/
    topology.schema.yaml
    rules.schema.yaml
    dpdkd-ipc.schema.json
    ctrld-api.openapi.yaml

  dpdkd/
    meson.build
    include/
      pktlab_dpdkd/
        api.h
        types.h
        errors.h
        version.h
    src/
      main.c
      daemon.c
      daemon.h
      eal.c
      eal.h
      ports.c
      ports.h
      parser.c
      parser.h
      rules.c
      rules.h
      rule_table.c
      rule_table.h
      actions.c
      actions.h
      datapath.c
      datapath.h
      stats.c
      stats.h
      ipc_server.c
      ipc_server.h
      json_proto.c
      json_proto.h
      health.c
      health.h
      log.c
      log.h
      util.c
      util.h
    tests/
      unit/
      integration/

  ctrld/
    pyproject.toml
    pktlab_ctrld/
      __init__.py
      main.py
      app.py
      config/
        __init__.py
        topology.py
        rules.py
        validation.py
      api/
        __init__.py
        app.py
        models.py
        routes_health.py
        routes_topology.py
        routes_rules.py
        routes_stats.py
        routes_capture.py
        routes_scenario.py
      dpdk_client/
        __init__.py
        client.py
        protocol.py
        models.py
      topology/
        __init__.py
        manager.py
        namespaces.py
        links.py
        routes.py
        taps.py
      process/
        __init__.py
        supervisor.py
      state/
        __init__.py
        desired.py
        observed.py
        reconcile.py
      metrics/
        __init__.py
        exporter.py
      logging/
        __init__.py
        setup.py
      capture/
        __init__.py
        manager.py
      scenario/
        __init__.py
        runner.py
      util/
        subprocess.py
        netns.py
        time.py
      error.py
      types.py
    tests/
      integration/

  ctl/
    pyproject.toml
    pktlabctl/
      __init__.py
      main.py
      cli.py
      client.py
      output.py
      commands/
        __init__.py
        status.py
        topology.py
        rules.py
        capture.py
        scenario.py

  traffic/
    gen_scapy.py
    verify.py
    replay_pcap.sh
    scenarios/
      udp_dns_mix.py
      tcp_mixed.py
      icmp_smoke.py

  lab/
    topologies/
      linear.yaml
      mirror.yaml
      multi-hop.yaml
    scripts/
      dev-up.sh
      dev-down.sh
      tcpdump.sh

  monitoring/
    prometheus.yml
    grafana/
      dashboards/
        pktlab-overview.json
```

---

# 4. Build and Packaging Strategy

## 4.1 Build tools

- `dpdkd/`: Meson + Ninja
- `ctrld/`: Python package via `pyproject.toml`
- `ctl/`: Python package via `pyproject.toml`
- top-level `Makefile`: orchestration only

## 4.2 Root Make targets

Provide these:

```make
make build
make build-dpdkd
make install-py
make test
make test-dpdkd
make test-py
make fmt
make lint
make clean
make run-dev
```

## 4.3 Python runtime requirements

Recommended Python version: **3.11+**

Recommended Python dependencies:
- `pydantic` or `dataclasses` + validation helpers
- `PyYAML`
- `FastAPI` or `Flask` for HTTP API
- `uvicorn` if FastAPI is used
- `requests` or `httpx` for CLI client
- `prometheus_client`
- `structlog` or `logging` with JSON formatter

Important design rule:
- do not overcomplicate the controller framework stack
- favor readability over trendy abstractions

---

# 5. Runtime Topology Model

## 5.1 Base topology

```text
[tg-src] -- veth -- [dpdk-host] -- veth -- [tg-sink]
                   |
                   +-- TAP interfaces used by pktlab-dpdkd
                   +-- capture points
                   +-- controller-visible management
```

## 5.2 Recommended namespaces

Required:
- `tg-src`
- `dpdk-host`
- `tg-sink`

Optional:
- `mon`
- `ctrl`

MVP simplification:
- allow `pktlab-ctrld` to run in host namespace

---

# 6. IPC Design: Controller to Datapath

## 6.1 Transport

Use:
- Unix domain stream socket
- local-only
- length-prefixed JSON messages

Socket path:

```text
/run/pktlab/dpdkd.sock
```

## 6.2 Message framing

Each message is:
- 4-byte big-endian unsigned length
- UTF-8 JSON payload of that length

Format:

```text
[len][json_payload]
```

This framing must be identical in C and Python.

## 6.3 Request format

```json
{
  "id": "req-0001",
  "cmd": "get_stats",
  "payload": {}
}
```

## 6.4 Success response format

```json
{
  "id": "req-0001",
  "ok": true,
  "payload": {
    "stats": {
      "rx_packets": 1000,
      "tx_packets": 900,
      "drop_packets": 100,
      "drop_parse_errors": 0,
      "drop_no_match": 100,
      "rx_bursts": 50,
      "tx_bursts": 45,
      "unsent_packets": 0,
      "rule_hits": {
        "10": 900
      }
    }
  }
}
```

## 6.5 Error response format

```json
{
  "id": "req-0001",
  "ok": false,
  "error": {
    "code": "RULE_VALIDATION_ERROR",
    "message": "duplicate rule id 10"
  }
}
```

## 6.6 Command set

Required commands:
- `ping`
- `get_version`
- `get_health`
- `get_ports`
- `get_stats`
- `reset_stats`
- `get_rules`
- `replace_rules`
- `pause_datapath`
- `resume_datapath`
- `shutdown`

Optional MVP commands:
- `add_rule`
- `delete_rule`

Preferred control pattern:
- controller sends full rule table using `replace_rules`
- datapath validates and atomically swaps the active rule table

---

# 7. Exact IPC Models

## 7.1 Common semantic model: Rule

### Rule object

```json
{
  "id": 10,
  "priority": 10,
  "match": {
    "proto": "udp",
    "dst_port": 53
  },
  "action": {
    "type": "forward",
    "port": "dtap1"
  }
}
```

### Match fields
- `proto`: `tcp | udp | icmp | any`
- `src_ip`: IPv4 dotted string optional
- `dst_ip`: IPv4 dotted string optional
- `src_cidr`: CIDR string optional
- `dst_cidr`: CIDR string optional
- `src_port`: integer optional
- `dst_port`: integer optional

### Action fields
- `type`: `forward | drop | count | mirror`
- `port`: required for `forward` and `mirror`, omitted otherwise

## 7.2 Replace rules request

```json
{
  "id": "req-0020",
  "cmd": "replace_rules",
  "payload": {
    "rule_version": 3,
    "default_action": {
      "type": "drop"
    },
    "rules": [
      {
        "id": 10,
        "priority": 10,
        "match": {
          "proto": "udp",
          "dst_port": 53
        },
        "action": {
          "type": "forward",
          "port": "dtap1"
        }
      }
    ]
  }
}
```

## 7.3 Replace rules response

```json
{
  "id": "req-0020",
  "ok": true,
  "payload": {
    "applied_rule_version": 3,
    "rule_count": 1
  }
}
```

## 7.4 Health response payload

```json
{
  "health": {
    "state": "running",
    "message": "datapath active",
    "applied_rule_version": 3,
    "ports_ready": true,
    "paused": false
  }
}
```

## 7.5 Ports response payload

```json
{
  "ports": [
    {
      "name": "dtap0",
      "port_id": 0,
      "role": "ingress",
      "state": "up"
    },
    {
      "name": "dtap1",
      "port_id": 1,
      "role": "egress",
      "state": "up"
    }
  ]
}
```

## 7.6 Get rules response payload

```json
{
  "rule_version": 3,
  "default_action": {
    "type": "drop"
  },
  "rules": [
    {
      "id": 10,
      "priority": 10,
      "match": {
        "proto": "udp",
        "dst_port": 53
      },
      "action": {
        "type": "forward",
        "port": "dtap1"
      }
    }
  ]
}
```

---

# 8. Controller HTTP API

## 8.1 Required endpoints

- `GET /health`
- `GET /version`
- `GET /topology`
- `POST /topology/apply`
- `POST /topology/destroy`
- `GET /datapath/status`
- `GET /datapath/stats`
- `GET /rules`
- `PUT /rules`
- `POST /captures/start`
- `POST /captures/stop`
- `GET /captures`
- `POST /scenarios/run`

## 8.2 Important rule

This is the controller API, not the datapath API.

Clients should not need to know datapath internals.

---

# 9. CLI Commands

## 9.1 Required commands

- `pktlabctl status`
- `pktlabctl topology apply -f <file>`
- `pktlabctl topology destroy`
- `pktlabctl rules show`
- `pktlabctl rules replace -f <file>`
- `pktlabctl stats show`
- `pktlabctl capture start <name>`
- `pktlabctl capture stop <name-or-id>`
- `pktlabctl capture list`
- `pktlabctl scenario run <name>`

## 9.2 Output behavior

Support:
- human-readable output by default
- `--json` for machine-readable output

---

# 10. Config Model

## 10.1 Topology YAML example

```yaml
lab:
  name: linear-basic

processes:
  dpdkd:
    namespace: dpdk-host
    lcores: "1"
    hugepages_mb: 512
    burst_size: 32

  ctrld:
    rest_listen: "127.0.0.1:8080"
    metrics_listen: "127.0.0.1:9102"

namespaces:
  - name: tg-src
  - name: dpdk-host
  - name: tg-sink

links:
  - name: src-to-dpdk
    a: tg-src:eth0
    b: dpdk-host:veth-in-k
    ip_a: 10.0.0.2/24
    ip_b: 10.0.0.1/24

  - name: dpdk-to-sink
    a: dpdk-host:veth-out-k
    b: tg-sink:eth0
    ip_a: 10.0.1.1/24
    ip_b: 10.0.1.2/24

dpdk_ports:
  - name: dtap0
    namespace: dpdk-host
    role: ingress
  - name: dtap1
    namespace: dpdk-host
    role: egress

routes:
  - namespace: tg-src
    dst: 10.0.1.0/24
    via: 10.0.0.1

  - namespace: tg-sink
    dst: 10.0.0.0/24
    via: 10.0.1.1

rules:
  version: 1
  default_action:
    type: drop
  entries:
    - id: 10
      priority: 10
      match:
        proto: udp
        dst_port: 53
      action:
        type: forward
        port: dtap1

capture_points:
  - name: src-egress
    namespace: tg-src
    interface: eth0
  - name: dpdk-pre
    namespace: dpdk-host
    interface: veth-in-k
  - name: dpdk-post
    namespace: dpdk-host
    interface: veth-out-k
  - name: sink-ingress
    namespace: tg-sink
    interface: eth0
```

## 10.2 Validation rules

Validation must check:
- unique namespace names
- unique link names
- unique capture point names
- unique rule IDs
- valid IP/CIDR format
- valid route references
- valid port references in actions
- explicit `default_action`
- supported protocols and actions only

Parsing and validation must be separate steps.

---

# 11. C Datapath Data Models

## 11.1 Packet metadata

```c
struct pkt_meta {
    uint16_t ether_type;
    uint8_t l4_proto;
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint16_t pkt_len;
    uint8_t flags;
};
```

## 11.2 Rule action enum

```c
enum dp_action_type {
    DP_ACTION_FORWARD = 1,
    DP_ACTION_DROP = 2,
    DP_ACTION_COUNT = 3,
    DP_ACTION_MIRROR = 4
};
```

## 11.3 Rule match structure

```c
struct dp_rule_match {
    uint8_t proto;
    uint32_t src_ip;
    uint32_t dst_ip;
    uint32_t src_cidr_ip;
    uint32_t src_cidr_mask;
    uint32_t dst_cidr_ip;
    uint32_t dst_cidr_mask;
    uint16_t src_port;
    uint16_t dst_port;

    uint8_t has_src_ip;
    uint8_t has_dst_ip;
    uint8_t has_src_cidr;
    uint8_t has_dst_cidr;
    uint8_t has_src_port;
    uint8_t has_dst_port;
};
```

## 11.4 Rule structure

```c
struct dp_rule {
    uint32_t id;
    uint32_t priority;
    struct dp_rule_match match;
    enum dp_action_type action_type;
    uint16_t out_port_id;
};
```

## 11.5 Stats structure

```c
struct dp_stats_snapshot {
    uint64_t rx_packets;
    uint64_t tx_packets;
    uint64_t drop_packets;
    uint64_t drop_parse_errors;
    uint64_t drop_no_match;
    uint64_t rx_bursts;
    uint64_t tx_bursts;
    uint64_t unsent_packets;
};
```

---

# 12. Python Controller Data Models

## 12.1 Recommended modeling approach

Use either:
- `pydantic` models for external/API/config models
- `dataclasses` for internal state models

A practical split is:
- `pydantic` for config and API payload validation
- `dataclasses` for internal runtime state

## 12.2 Core Python models

### `RuleMatchModel`
Fields:
- `proto: Literal["tcp", "udp", "icmp", "any"] | None`
- `src_ip: str | None`
- `dst_ip: str | None`
- `src_cidr: str | None`
- `dst_cidr: str | None`
- `src_port: int | None`
- `dst_port: int | None`

### `RuleActionModel`
Fields:
- `type: Literal["forward", "drop", "count", "mirror"]`
- `port: str | None`

### `RuleModel`
Fields:
- `id: int`
- `priority: int`
- `match: RuleMatchModel`
- `action: RuleActionModel`

### `RulesetModel`
Fields:
- `version: int`
- `default_action: RuleActionModel`
- `entries: list[RuleModel]`

### `CapturePointModel`
Fields:
- `name: str`
- `namespace: str`
- `interface: str`

### `DesiredState`
Fields:
- `topology_config_path: str | None`
- `topology_name: str | None`
- `desired_rules_version: int | None`
- `desired_controller_state: str`
- `desired_datapath_running: bool`

### `ObservedState`
Fields:
- `datapath_health: str`
- `applied_rules_version: int | None`
- `dpdkd_pid: int | None`
- `active_captures: dict`
- `topology_applied: bool`

---

# 13. Example Request/Response Traces

## 13.1 Controller startup to datapath health check

### Request
```json
{
  "id": "req-start-001",
  "cmd": "ping",
  "payload": {}
}
```

### Response
```json
{
  "id": "req-start-001",
  "ok": true,
  "payload": {
    "message": "pong"
  }
}
```

### Follow-up request
```json
{
  "id": "req-start-002",
  "cmd": "get_health",
  "payload": {}
}
```

### Follow-up response
```json
{
  "id": "req-start-002",
  "ok": true,
  "payload": {
    "health": {
      "state": "running",
      "message": "datapath active",
      "applied_rule_version": 0,
      "ports_ready": true,
      "paused": false
    }
  }
}
```

## 13.2 Controller replacing rules

### Request
```json
{
  "id": "req-rules-001",
  "cmd": "replace_rules",
  "payload": {
    "rule_version": 2,
    "default_action": {
      "type": "drop"
    },
    "rules": [
      {
        "id": 10,
        "priority": 10,
        "match": {
          "proto": "udp",
          "dst_port": 53
        },
        "action": {
          "type": "forward",
          "port": "dtap1"
        }
      }
    ]
  }
}
```

### Response
```json
{
  "id": "req-rules-001",
  "ok": true,
  "payload": {
    "applied_rule_version": 2,
    "rule_count": 1
  }
}
```

---

# 14. Project-Wide Instructions for AI Coding Assistants

## 14.1 Project/system-wide instructions

These instructions apply to all modules.

### Architecture rules
1. Preserve the three-process model.
2. Do not merge controller and datapath into one process.
3. Do not make `pktlabctl` talk directly to `pktlab-dpdkd`.
4. Controller owns desired state.
5. Datapath owns fast-path execution and counters.
6. Keep controller-to-datapath communication over Unix socket IPC only.
7. Use full rule-table replacement as the preferred synchronization model.
8. Keep topology mutations serialized.
9. Keep packet capture managed by the controller, never by the datapath.
10. Expose Prometheus metrics from the controller, not from the datapath.

### Design rules
1. Prefer explicit code over clever abstractions.
2. Minimize hidden state.
3. Make side effects visible and logged.
4. Make state transitions explicit.
5. Keep desired and observed state separate.
6. Prefer boring code that is easy to test.
7. Avoid adding framework complexity unless it clearly improves the code.
8. Keep module responsibilities narrow.
9. Avoid introducing plugin systems or generic abstractions in the MVP.
10. Preserve readability for both humans and AI tools.

### Error handling rules
1. Every external operation must return a clear success or typed error.
2. Invalid input must not crash the process.
3. Unknown IPC commands must return a typed error response.
4. Topology apply/destroy must surface partial failure clearly.
5. Logs must contain enough context to debug failures.

### Performance rules
1. Fast path performance matters only in `pktlab-dpdkd`.
2. Python code must optimize for clarity, not micro-performance.
3. C datapath code must not allocate memory in the packet hot path.
4. C datapath code must not log per packet.
5. Control-plane IPC is allowed to be JSON because control-plane rate is low.

### AI-assistant behavior rules
1. Do not invent new protocols.
2. Do not silently rename fields across modules.
3. Reuse the exact schema names defined in this document.
4. Do not add optional fields without documenting them.
5. Do not infer ownership rules unless documented.
6. If a module needs another module’s functionality, call its public interface instead of duplicating logic.
7. If a module requires external command execution, centralize that in utility wrappers.
8. Favor idempotent operations when possible.

---

# 15. Per-Module Instructions for AI Coding Assistants

## 15.1 `dpdkd/src/main.c`

Purpose:
- entry point for datapath daemon

Responsibilities:
- parse CLI arguments
- initialize logging
- initialize daemon context
- call EAL init
- start IPC server
- start datapath worker
- install signal handlers
- perform graceful shutdown

Rules:
- keep `main.c` thin
- delegate real work to dedicated modules
- do not place datapath loop logic directly in `main.c`
- do not parse JSON in `main.c`

## 15.2 `dpdkd/src/eal.c`

Purpose:
- initialize DPDK EAL

Responsibilities:
- build EAL argv
- verify hugepages availability
- validate requested lcore configuration
- return clear init errors

Rules:
- do not hardcode machine-specific assumptions
- do not own rule/state logic
- log enough context for startup failures

## 15.3 `dpdkd/src/ports.c`

Purpose:
- port initialization and lifecycle

Responsibilities:
- configure each DPDK port
- set up RX/TX queues
- start and stop ports
- map logical port names to DPDK port IDs

Rules:
- isolate all DPDK port setup here
- do not mix rule logic here
- expose a simple lookup API for port name to port id

## 15.4 `dpdkd/src/parser.c`

Purpose:
- parse packet headers into `pkt_meta`

Responsibilities:
- parse Ethernet header
- parse IPv4 header
- parse TCP/UDP/ICMP where applicable
- return parse success/failure

Rules:
- never allocate memory
- never log per packet
- never perform policy decisions here
- output must be a plain metadata struct suitable for classifier use

## 15.5 `dpdkd/src/rule_table.c`

Purpose:
- represent active and replacement rule tables

Responsibilities:
- hold rule array
- sort rules by priority then ID
- provide lookup iteration API
- support safe replacement

Rules:
- MVP uses simple array-based rule table
- do not introduce hash tables or ACL libraries in first implementation
- keep replacement logic deterministic

## 15.6 `dpdkd/src/rules.c`

Purpose:
- validate and manage rule updates

Responsibilities:
- validate incoming rule payloads
- build new rule table
- atomically swap active pointer
- maintain applied rule version

Rules:
- reject invalid rule sets without disturbing active rules
- duplicate IDs must be rejected
- unsupported actions must be rejected

## 15.7 `dpdkd/src/actions.c`

Purpose:
- apply datapath actions

Responsibilities:
- forward packet to target port
- drop packet
- count packet without forwarding behavior change if supported
- mirror packet if implemented

Rules:
- keep actions explicit and small
- reclaim/free mbufs correctly on drop or unsent cases
- do not bury TX logic across multiple modules

## 15.8 `dpdkd/src/datapath.c`

Purpose:
- packet RX/classify/action/TX loop

Responsibilities:
- receive bursts
- parse packets
- match rules
- apply actions
- send packets
- update counters

Rules:
- this is hot path code
- no heap allocation in loop
- no string formatting in loop
- no control-plane concerns in loop
- use readable small helper functions where needed

## 15.9 `dpdkd/src/stats.c`

Purpose:
- manage datapath counters

Responsibilities:
- own stats struct(s)
- update counters efficiently
- provide snapshot function
- reset counters on request

Rules:
- snapshot API must be IPC-friendly
- do not expose mutable internal pointers outside this module

## 15.10 `dpdkd/src/health.c`

Purpose:
- health state tracking for datapath daemon

Responsibilities:
- maintain explicit daemon health state
- provide current health snapshot

Rules:
- do not infer health from arbitrary counters
- state must be explicit and set by lifecycle code

## 15.11 `dpdkd/src/json_proto.c`

Purpose:
- encode/decode bounded JSON protocol structures

Responsibilities:
- parse incoming JSON requests from IPC server
- serialize success/error responses
- validate required fields are present

Rules:
- keep JSON handling isolated to this module and IPC server
- invalid JSON must never crash the process
- never let JSON parsing logic leak into datapath loop

## 15.12 `dpdkd/src/ipc_server.c`

Purpose:
- Unix socket server for local control messages

Responsibilities:
- create/listen on socket
- read length-prefixed frames
- parse request JSON
- dispatch to handler functions
- write response JSON

Rules:
- preserve message ID in responses
- unknown commands return typed error
- do not block datapath loop unnecessarily
- separate transport handling from command dispatch logic

---

## 15.13 `ctrld/pktlab_ctrld/main.py`

Purpose:
- controller process entry point

Responsibilities:
- initialize logging
- load app configuration
- construct controller app object
- start HTTP server
- manage shutdown hooks

Rules:
- keep this file thin
- do not place topology logic directly here

## 15.14 `ctrld/pktlab_ctrld/app.py`

Purpose:
- controller composition root

Responsibilities:
- wire together config, state, topology manager, process supervisor, datapath client, capture manager, metrics exporter

Rules:
- this module may compose objects but should not become a dumping ground for business logic

## 15.15 `ctrld/pktlab_ctrld/config/topology.py`

Purpose:
- parse topology YAML into typed models

Responsibilities:
- load YAML
- deserialize into typed topology models

Rules:
- parsing only, no validation side effects here
- model names must match schema names closely

## 15.16 `ctrld/pktlab_ctrld/config/validation.py`

Purpose:
- validate parsed topology and rules

Responsibilities:
- uniqueness checks
- link reference checks
- route checks
- action target checks
- protocol/action enum checks

Rules:
- validation must return structured error objects
- do not mix subprocess or topology mutation here

## 15.17 `ctrld/pktlab_ctrld/dpdk_client/protocol.py`

Purpose:
- shared protocol helpers for controller-to-datapath IPC

Responsibilities:
- encode request JSON
- frame length prefix
- decode responses
- validate basic response shape

Rules:
- this module is the only Python module allowed to know IPC framing details
- do not duplicate framing logic elsewhere

## 15.18 `ctrld/pktlab_ctrld/dpdk_client/models.py`

Purpose:
- Python models for datapath IPC request/response payloads

Responsibilities:
- define typed request and response models
- keep field names aligned with JSON schema

Rules:
- do not mix controller REST models with datapath IPC models
- they may look similar but are different API layers

## 15.19 `ctrld/pktlab_ctrld/dpdk_client/client.py`

Purpose:
- concrete client for `pktlab-dpdkd`

Responsibilities:
- open Unix socket
- send framed requests
- receive responses
- expose typed methods like `ping()`, `get_health()`, `replace_rules()`

Rules:
- all socket error handling must be explicit
- timeouts must be configurable
- all methods must return typed success/error results

## 15.20 `ctrld/pktlab_ctrld/topology/manager.py`

Purpose:
- high-level topology apply/destroy orchestrator

Responsibilities:
- apply topology in correct order
- destroy topology in reverse-safe order
- keep operations serialized

Rules:
- use submodules for namespaces, links, routes, taps
- no direct shell command construction outside utility wrappers
- apply must be as idempotent as practical

## 15.21 `ctrld/pktlab_ctrld/topology/namespaces.py`

Purpose:
- create/delete/check Linux namespaces

Responsibilities:
- create namespace
- delete namespace
- list existing namespaces if needed

Rules:
- centralize namespace operations here
- do not scatter `ip netns` calls across project

## 15.22 `ctrld/pktlab_ctrld/topology/links.py`

Purpose:
- create/delete/configure veth links

Responsibilities:
- create veth pairs
- move interfaces into namespaces
- assign names
- bring links up
- assign addresses

Rules:
- preserve deterministic interface naming
- log all created/deleted links

## 15.23 `ctrld/pktlab_ctrld/topology/routes.py`

Purpose:
- configure routes inside namespaces

Responsibilities:
- install routes
- remove routes if needed
- verify route operations succeeded

Rules:
- route changes must be explicit and logged
- avoid silent overwrites

## 15.24 `ctrld/pktlab_ctrld/topology/taps.py`

Purpose:
- create/manage TAP interfaces required by DPDK lab topology

Responsibilities:
- create TAP interfaces in correct namespace
- set interface state
- ensure names match DPDK config

Rules:
- do not assume TAP interfaces already exist
- do not create TAPs in multiple places

## 15.25 `ctrld/pktlab_ctrld/process/supervisor.py`

Purpose:
- launch and supervise `pktlab-dpdkd`

Responsibilities:
- spawn process with expected args
- detect readiness via socket ping/health
- detect unexpected exit
- terminate or restart if configured

Rules:
- process startup is not considered successful until IPC readiness is confirmed
- keep restart logic simple and explicit

## 15.26 `ctrld/pktlab_ctrld/state/desired.py`

Purpose:
- desired state models

Responsibilities:
- represent what controller wants the lab to look like

Rules:
- desired state must not contain derived runtime values

## 15.27 `ctrld/pktlab_ctrld/state/observed.py`

Purpose:
- observed state models

Responsibilities:
- represent what the system currently reports

Rules:
- observed state must come from live inspection, not assumptions

## 15.28 `ctrld/pktlab_ctrld/state/reconcile.py`

Purpose:
- compare desired and observed state

Responsibilities:
- determine whether topology/rules/processes need changes
- provide explicit reconciliation actions

Rules:
- keep reconciliation logic deterministic
- do not perform side effects while computing a plan unless explicitly designed to do so

## 15.29 `ctrld/pktlab_ctrld/api/app.py`

Purpose:
- construct HTTP API application

Responsibilities:
- register routes
- inject controller services

Rules:
- keep route handlers thin
- business logic should live in service modules

## 15.30 `ctrld/pktlab_ctrld/api/models.py`

Purpose:
- REST request/response models

Responsibilities:
- define controller-facing API payloads

Rules:
- keep these separate from datapath IPC models
- they may wrap or translate datapath structures

## 15.31 `ctrld/pktlab_ctrld/metrics/exporter.py`

Purpose:
- expose Prometheus metrics

Responsibilities:
- publish controller health
- publish datapath snapshots
- publish topology state
- publish capture/scenario state if useful

Rules:
- scrape datapath via controller polling, not direct Prometheus in C daemon
- metric names should be stable and documented

## 15.32 `ctrld/pktlab_ctrld/capture/manager.py`

Purpose:
- manage packet captures at named capture points

Responsibilities:
- start `tcpdump` in namespace
- stop capture subprocesses
- track running captures
- return file paths and status

Rules:
- captures are first-class features
- capture point names must come from topology config
- do not let datapath manage captures

## 15.33 `ctrld/pktlab_ctrld/scenario/runner.py`

Purpose:
- run traffic generation and verification scenarios

Responsibilities:
- invoke traffic scripts or external tools
- capture scenario status and exit code
- return structured results

Rules:
- scenarios are operational helpers, not part of datapath logic
- keep scenario execution isolated from topology management

## 15.34 `ctl/pktlabctl/main.py`

Purpose:
- CLI entry point

Responsibilities:
- parse arguments
- dispatch to command modules

Rules:
- keep it thin
- do not put HTTP logic directly in `main.py`

## 15.35 `ctl/pktlabctl/client.py`

Purpose:
- HTTP client for controller API

Responsibilities:
- call controller endpoints
- handle errors and timeouts
- return parsed models

Rules:
- only talk to controller API
- centralize HTTP request behavior here

## 15.36 `ctl/pktlabctl/output.py`

Purpose:
- formatting for human and JSON output

Responsibilities:
- pretty print default output
- emit raw JSON when requested

Rules:
- avoid business logic here
- formatting only

---

# 16. Controller State Machine

## 16.1 Controller states

Allowed controller states:
- `stopped`
- `starting`
- `running`
- `degraded`
- `reconciling`
- `stopping`
- `failed`

These states must be modeled explicitly.

## 16.2 Datapath states

Allowed datapath states:
- `starting`
- `running`
- `paused`
- `degraded`
- `stopping`
- `failed`

These states must be surfaced via `get_health`.

---

# 17. Capture Design

## 17.1 Capture point model

Capture points are config-defined and named.

Example:

```yaml
capture_points:
  - name: dpdk-pre
    namespace: dpdk-host
    interface: veth-in-k
```

## 17.2 Capture process model

Controller starts captures using namespace-aware subprocess execution, for example:

```bash
ip netns exec dpdk-host tcpdump -i veth-in-k -w /tmp/dpdk-pre.pcap
```

This must be launched through centralized subprocess helpers.

---

# 18. Suggested Development Order

## Phase 1
Implement:
- datapath IPC stub server in C
- Python datapath IPC client
- controller health endpoint
- process supervisor
- CLI status command

## Phase 2
Implement:
- topology config parsing and validation
- namespace creation/deletion
- veth and route setup
- TAP creation

## Phase 3
Implement:
- datapath pass-through forwarding
- basic stats
- readiness checks

## Phase 4
Implement:
- rule parsing and validation
- full `replace_rules`
- rule counters
- REST rule endpoints

## Phase 5
Implement:
- Prometheus exporter
- capture manager
- scenario runner
- better CLI output

---

# 19. Non-Goals for MVP

The first implementation must not attempt:
- multi-lcore datapath
- binary IPC
- plugin frameworks
- HA controller
- distributed lab across multiple machines
- auth-heavy production REST concerns
- GUI topology editor
- RCU-like advanced rule synchronization

Those can wait. The MVP does not need a cape.

---

# 20. First Files to Implement

## 20.1 Schema files
Create first:
- `schemas/dpdkd-ipc.schema.json`
- `schemas/topology.schema.yaml`

## 20.2 C datapath files
Create first:
- `dpdkd/include/pktlab_dpdkd/types.h`
- `dpdkd/include/pktlab_dpdkd/errors.h`
- `dpdkd/src/json_proto.h`
- `dpdkd/src/ipc_server.h`
- `dpdkd/src/health.h`
- `dpdkd/src/stats.h`

## 20.3 Python controller files
Create first:
- `ctrld/pktlab_ctrld/types.py`
- `ctrld/pktlab_ctrld/error.py`
- `ctrld/pktlab_ctrld/dpdk_client/protocol.py`
- `ctrld/pktlab_ctrld/dpdk_client/models.py`
- `ctrld/pktlab_ctrld/dpdk_client/client.py`
- `ctrld/pktlab_ctrld/state/desired.py`
- `ctrld/pktlab_ctrld/state/observed.py`
- `ctrld/pktlab_ctrld/config/topology.py`
- `ctrld/pktlab_ctrld/config/validation.py`

## 20.4 CLI files
Create first:
- `ctl/pktlabctl/client.py`
- `ctl/pktlabctl/commands/status.py`
- `ctl/pktlabctl/output.py`

---

# 21. Final Instruction Summary for AI Assistants

1. Implement the control plane in Python and datapath in C.
2. Keep the process boundary strict.
3. Use Unix socket + length-prefixed JSON for controller-to-datapath IPC.
4. Use YAML for topology configuration.
5. Use full rule-set replacement as the default synchronization pattern.
6. Keep the datapath simple and explicit.
7. Keep the controller authoritative for desired state.
8. Keep packet capture and observability in the controller.
9. Avoid unnecessary abstraction layers.
10. Prioritize correctness, debuggability, and readability over cleverness.

