# Design notes

Why the model looks like this. Three decisions carry the rest.

## 1. One accountable owner per task

"Which agent should pick this up?" is the question every fleet gets wrong first. If two seats can
own a task, nobody owns it. So every seat declares a set of routing `signals`, and
`governance/router.py` scores them deterministically: a signal hit counts double, a title word
counts once, ties break on the lowest seat id. No embeddings, no model calls - the routing decision
has to be greppable, unit-testable and predictable in review.

When nothing matches, the router does not guess. It routes to the default triage seat (`D1`), marks
the plan `unrouted: true`, and `--strict` turns that into a non-zero exit code, which is what you
want in CI.

## 2. Autonomy belongs to the plane, not the individual

A seat that can act without asking is only safe if the plane it acts on carries a `verification`
and an `approvals` contract. That is why the auditor checks the *plane*, not the seat: a fleet can
have one careful L4 engineer and still be one unguarded plane away from an incident.

```
L0 propose ── L1 draft ── L2 act-and-report ── L3 act-with-verification ── L4 run-the-plane
          escalation above L2 requires an approval contract bound to the plane
```

## 3. Cost is a contract too

A cost tier that nothing reads is decoration. `roles.json` declares a daily ceiling per tier;
`governance/budget.py` compares one day of spend per seat against the ceiling of the tier that seat
sits on and returns findings, not prose. Same shape as the auditor: machine-readable, exit code,
zero surprise in review.

## What the pieces are

| Path | Job |
| --- | --- |
| `roles/roles.json` | the roster: 24 seats, each with tier, plane, autonomy, cost tier, mandate, signals |
| `planes/planes.json` | the contract layout: 8 failure domains, their owners, and the contracts they bind |
| `governance/audit.py` | the trust mechanism: 14 rule codes, non-zero exit on any finding |
| `governance/router.py` | task to seat, with the approval gate and the plane contracts attached |
| `governance/budget.py` | per-tier cost ceilings and spend findings |
| `telemetry/collector.py` | one host sample, hostname redacted by default |
| `telemetry/ledger.py` | the same samples over time: rollups and threshold alerts |

## Deliberate non-goals

- **Not a framework.** Nothing here runs your agents. It decides who is accountable and proves it.
- **No model calls.** A governance layer that needs an LLM to say who is accountable is not a
  governance layer.
- **No hostnames by default.** A published sample has to be safe to publish, so `include_host` is
  opt-in and off.
- **No vendor SDKs.** The whole model is stdlib, so it runs on the box you already have.
