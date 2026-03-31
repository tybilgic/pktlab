# pktlab Working Workflow

## Goal

Keep implementation resumable, auditable, and easy to continue across sessions without repeating planning work.

## Session Start Protocol

1. Read [docs/progress.md](progress.md).
2. Open the active ticket from [docs/tickets/README.md](tickets/README.md).
3. Review the latest related commit(s).
4. Inspect only the files relevant to the active ticket and any files changed after the last recorded update.

This keeps continuity high while still grounding work in the current repository state.

## Ticket Status Model

Allowed values:
- `not started`
- `in progress`
- `blocked`
- `done`

`docs/progress.md` is the source of truth for status.

## Implementation Protocol

For each ticket:

1. Re-read the ticket scope and acceptance criteria.
2. Implement one coherent vertical slice.
3. Run the smallest relevant verification for that slice.
4. Update [docs/progress.md](progress.md):
   - status
   - what changed
   - what remains
   - follow-up risks or blockers
5. Create a scoped commit with a structured commit message.

## Commit Policy

Commits should be:

- small enough to review
- large enough to leave the codebase in a coherent state
- documented in plain language
- scoped to one ticket or one coherent sub-slice of a ticket
- written so a future reader can understand the change without reopening the whole diff

Required commit message shape:

```text
<area>: <what the change achieves>

Why:
- why this change is necessary now

Approach:
- how the change solves the problem

Tradeoffs:
- optional, include when an alternative approach was considered or deferred
```

Examples:

```text
schemas: define the initial topology and IPC contracts

Why:
- later C and Python modules need one shared contract to avoid drift

Approach:
- add frozen schema files before implementing transport or parsing logic

ctrld: add unix socket health checks for datapath supervision

Why:
- controller readiness depends on confirmed IPC health, not just process spawn

Approach:
- add a typed datapath client and use it from the supervisor readiness path

topology: add namespace and veth lifecycle primitives

Why:
- topology apply/destroy needs centralized ownership of kernel-visible lab objects

Approach:
- isolate namespace and link operations in dedicated modules instead of scattering shell calls

dpdkd: start TAP PMD ports for controller-managed lab topology

Why:
- the datapath must create dtap interfaces while the controller remains topology authority

Approach:
- launch TAP PMD devices from dpdkd and let the controller reconcile them into bridges after startup

Tradeoffs:
- this keeps ownership boundaries explicit, at the cost of a delayed interface binding step
```

Commit message guidance:

- the subject line should say what the change achieves, not just what files changed
- `Why` is required
- `Approach` is required
- `Tradeoffs` is required when there was a meaningful design choice, compromise, or deferred alternative
- avoid vague subjects such as `fix stuff`, `updates`, or `wip`
- if a change spans multiple concerns, split it into smaller commits

## Progress Update Format

When a ticket changes state, record:

- date
- ticket id
- status
- summary of implemented work
- files touched
- verification run
- next step
- related commit hash once committed
- commit subject

## Resuming After Interruptions

When work stops mid-ticket:

- leave the ticket `in progress`
- add a short handoff note in [docs/progress.md](progress.md)
- record the exact next technical step

## Reality Check

These documents let us carry context forward, but they do not eliminate the need to check the current code and git state. They are intended to minimize repeated exploration, not replace it.
