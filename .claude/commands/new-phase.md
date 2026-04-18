Scaffold a new phase plan document. The user will provide a phase number and title (e.g. `/new-phase 4 "Run Analytics"`).

Create `docs/PLAN_PHASE<N>.md` using the standard structure from this project:

```
# Phase N: <Title> — Implementation Plan (or Implementation Record if in progress)

## Context

[2-3 sentences: what the previous phase delivered and why this phase is needed]

---

## What Was Planned

### Na. <Sub-task name>
[Description of what was planned]

### Nb. <Sub-task name>
[Description of what was planned]

---

## What Was Built

_To be filled in during implementation._

---

## Bugs Found During Implementation

_To be filled in during implementation._

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **Na. <name>** | ⬜ Planned | |
| **Nb. <name>** | ⬜ Planned | |

---

## Deferred Items (carry into Phase N+1)

Items carried from Phase N-1 — not in scope for Phase N:

1. [Carried item from previous phase if any]
```

Status icons: ⬜ Planned, 🔄 In Progress, ✅ Done, ❌ Deferred, [~] Partial

Also add a placeholder entry for the new phase in `docs/PLAN.md` under the appropriate section, following the same pattern as the existing phase entries.

Ask the user for the phase number and title if not provided.
