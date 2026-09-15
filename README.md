# Agent Operating Model

**One box. 24 named seats. 8 planes. Nobody owns "everything".**

[![CI](https://github.com/Amz34/agent-operating-model/actions/workflows/ci.yml/badge.svg)](https://github.com/Amz34/agent-operating-model/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-15%20passing-brightgreen.svg)](#verified-numbers)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#quickstart)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs](https://img.shields.io/badge/PRs-welcome-orange.svg)](#fork-it-and-make-it-yours)

Role specifications, telemetry collectors and the multi-plane contract layout behind a governed
multi-agent organisation — the part that normally stays in someone's head until it breaks.

## The problem

Hand a model a shell and tasks get done. Run forty of them in parallel and you get the failures
everyone hits in week two:

- nobody can say **which seat** should have owned a task;
- autonomy gets granted by accident — a prompt tweak turns "draft this" into "deploy this";
- the one agent that verifies work belongs to the same chain that produced it;
- you cannot answer *"was it slow, or was it wrong?"* because nothing samples the box.

This repo is the boring scaffolding that removes those four. It is not a framework: it is data plus
two small standard-library tools, so it drops into whatever runtime you already use.

## What's inside

| Path | What it is |
|---|---|
| `roles/roles.json` | 24 seat specifications: id, title, tier, plane, autonomy level, cost tier, mandate, routing signals |
| `planes/planes.json` | 8 planes (P0–P7) + the **contract layout**: which seat owns each fleet-wide contract, and which contracts each plane binds |
| `governance/levels.json` | The L0–L4 autonomy ladder in plain language + the escalation ladder |
| `governance/audit.py` | The auditor. Checks the whole model, exits non-zero on findings. |
| `telemetry/collector.py` | Sampling collector: load, memory, disk, process pressure, uptime → one flat JSON record per tick |
| `telemetry/schema.json` | The record contract (hostname is opt-in, so a ledger stays safe to share) |
| `tests/` | 15 tests: the model passes its own rules, and every rule actually fires when violated |

## Quickstart

```bash
git clone https://github.com/Amz34/agent-operating-model
cd agent-operating-model

python -m governance.audit          # 24 seats across 8 planes -> clean
python -m telemetry.collector       # one sample, ~10 ms
python -m pytest -q                 # 15 passed
```

Nothing to install: Python 3.11+ and the standard library. `pytest` is the only dev dependency.

## The contract layout (the part people get wrong)

A contract is not a document. It is a **seat that owns a guarantee**, and planes that must honour it.
The layout shipped here binds five:

| Contract | Owner | Guarantee |
|---|---|---|
| `verification` | D12 | a verdict from a seat outside the producing chain |
| `approvals` | D21 | the human checkpoint and the rollback path |
| `security` | D13 | secrets, redaction, injection defence |
| `deploy` | D5 | preview first, production only after |
| `telemetry` | D24 | per-seat SLO and cost attribution |

Any plane granting **L3 or higher** must bind `verification` **and** `approvals`. That is enforced by
`E_UNGUARDED` in the auditor — not by a paragraph in a wiki that nobody reads at 2am.

## Autonomy ladder

| Level | Name | What the agent may do |
|---|---|---|
| `L0` | human-decides | inform only |
| `L1` | ai-advises | analyse and propose; a human performs the action |
| `L2` | ai-recommends | draft and prepare artefacts; a human reviews and applies |
| `L3` | agent-with-approval | execute end-to-end behind an approval checkpoint + mandatory verification |
| `L4` | agent-owned | full ownership inside a measured envelope, with rollback |

Escalation when something looks wrong: self-check → one retry → verification seat → approval queue →
chief of staff → owner (L0 only).

## Audit rules

Each rule is a failure we hit for real, not a hypothetical:

| Code | Catches |
|---|---|
| `E_DUP_ID` / `E_ROSTER` | two seats sharing an id, or a roster with a hole in it |
| `E_PLANE` / `E_LEVEL` / `E_COST` | a seat pointing at a plane, autonomy level or cost tier that does not exist |
| `E_MANDATE` | a mandate too thin to enforce |
| `E_EMPTY_PLANE` / `E_OWNER` / `E_SEAT_COUNT` | a plane with no seat, or an owner who is not on the roster |
| `E_CONTRACT` | a contract whose owner seat was deleted |
| `E_UNGUARDED` | L3+ granted on a plane that binds no guardrail contract |
| `E_LADDER` | an autonomy ladder with no escalation path |

```bash
python -m governance.audit --json     # machine-readable report for CI
python -m governance.audit --roles my-org/roles.json --planes my-org/planes.json
```

## Verified numbers

| Claim | How to check it |
|---|---|
| 24 seats, 8 planes, 5 autonomy levels | `python -m governance.audit` |
| 15 tests pass | `python -m pytest -q` |
| CI green on 3.11 and 3.12 | the badge above |
| Model passes its own rules | `test_shipped_model_is_clean` |
| Sampling costs < 10 ms | the `sample_ms` field on any record |

## Fork it and make it yours

The valuable part is not the roster, it is that the roster is **checkable**. Fork this and:

1. **Rewrite `roles/roles.json` for your own org.** Keep ids contiguous, keep autonomy honest. The
   auditor will tell you what you broke.
2. **Add a contract** (e.g. `cost`, `privacy`, `rollback`) and bind it to the planes that need it.
3. **Wire `collector.py` to your ledger** — 30-second ticks on a free-tier box cost under 10 ms each.
4. **PR the audit rule you wish existed.** Rule + failing test + one paragraph is a complete
   contribution, and the most useful kind of issue to open here.

Good first issues: a `--strict` mode that treats warnings as errors · an HTML report · a JSON Schema
for `roles.json` · a GitHub Action that audits a PR that touches a roster.

## How I use it

This model runs a 24-seat organisation on one 2-OCPU box: every task has one owner, every write has a
gate, and the telemetry ledger is what the autonomy levels are calibrated against. When a plane starts
failing its SLO, the fix is a role change — not a new framework.

If you want this wired into your own setup, that is the work I do; the model here is free and stays
free (MIT). Open an issue describing your fleet and I will tell you which two planes to fix first.

## License

MIT — see [LICENSE](LICENSE).
