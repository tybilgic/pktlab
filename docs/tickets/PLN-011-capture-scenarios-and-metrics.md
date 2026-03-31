# PLN-011 Capture Scenarios And Metrics

## Status

`not started`

## Goal

Add the operational tooling that makes the lab useful for experimentation: captures, scenarios, and metrics.

## Why This Exists

The project is not just a datapath demo; it is a reproducible and observable lab. This ticket delivers that operator value.

## Depends On

- `PLN-007`
- `PLN-009`
- `PLN-010`

## Scope

- implement:
  - `ctrld/pktlab_ctrld/capture/manager.py`
  - `ctrld/pktlab_ctrld/scenario/runner.py`
  - `ctrld/pktlab_ctrld/metrics/exporter.py`
  - `ctrld/pktlab_ctrld/api/routes_capture.py`
  - `ctrld/pktlab_ctrld/api/routes_scenario.py`
  - `ctl/pktlabctl/commands/capture.py`
  - `ctl/pktlabctl/commands/scenario.py`
- add operational assets:
  - `traffic/gen_scapy.py`
  - `traffic/verify.py`
  - `traffic/scenarios/*`
  - `lab/scripts/*`
  - `monitoring/prometheus.yml`
  - `monitoring/grafana/dashboards/pktlab-overview.json`

## Out Of Scope

- GUI workflows
- auth-heavy production concerns

## Implementation Notes

- capture point names come from topology config
- launch `tcpdump` via centralized subprocess helpers
- scrape datapath via controller polling, not direct Prometheus in C
- keep scenario execution isolated from topology mutation logic

## Acceptance Criteria

- captures can be started, listed, and stopped by name
- scenarios can be run and return structured results
- controller exposes stable Prometheus metrics
- example monitoring config works against the local lab

## Verification

- integration tests for capture start/stop
- scenario smoke tests
- metrics endpoint smoke test and simple scrape validation

## Suggested Commit Slices

- `capture: add namespace-aware capture manager`
- `scenario: add runner and API surface`
- `metrics: add controller prometheus exporter and monitoring assets`

## Handoff Note

Keep these features operationally useful but not over-engineered. They are helpers, not a new architecture layer.
