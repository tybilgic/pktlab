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
5. Create a scoped commit.

## Commit Policy

Commits should be:

- small enough to review
- large enough to leave the codebase in a coherent state
- documented in plain language

Recommended commit message shape:

```text
<area>: <what changed>
```

Examples:

```text
schemas: add initial topology and IPC contracts
ctrld: add dpdk unix socket client and health checks
topology: implement namespace and veth lifecycle helpers
dpdkd: add TAP PMD startup and port discovery
```

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

## Resuming After Interruptions

When work stops mid-ticket:

- leave the ticket `in progress`
- add a short handoff note in [docs/progress.md](progress.md)
- record the exact next technical step

## Reality Check

These documents let us carry context forward, but they do not eliminate the need to check the current code and git state. They are intended to minimize repeated exploration, not replace it.
