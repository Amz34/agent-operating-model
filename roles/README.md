# Seat specifications

One file, one roster: `roles.json`. A seat is a **job description a machine can be held to**.

| Field | Meaning |
|---|---|
| `id` | `D1`…`Dn`, contiguous. Every task resolves to exactly one of these. |
| `title` | What the seat is. Keep it human-readable — this is what shows up in a report. |
| `tier` | `command`, `build`, `assurance`, `intelligence`, `growth`, `new` — how the seat relates to the others. |
| `plane` | Which plane the seat sits on (`P0`–`P7`). |
| `autonomy` | `L0`–`L4`: the maximum this seat may do without a human. |
| `cost_tier` | `T0`–`T4`: how expensive its work is allowed to get. |
| `mandate` | One sentence, at least 20 characters. If you cannot state it, you cannot enforce it. |
| `signals` | Routing keywords: how an incoming task finds this seat. |

```json
{
  "id": "D12",
  "title": "QA & Verification Engineer",
  "tier": "assurance",
  "plane": "P4",
  "autonomy": "L4",
  "cost_tier": "T3",
  "mandate": "Independent verification; a verdict from a different provider than the producer.",
  "signals": ["verification", "verify", "self-qa", "audit", "independent check", "ledger"]
}
```

## Rules that bite

- **Ids are contiguous.** A hole in the roster means a task with no owner (`E_ROSTER`).
- **Autonomy is a ceiling, not a mood.** If a plane grants L3+, it must bind the `verification` and
  `approvals` contracts (`E_UNGUARDED`).
- **A verifier cannot verify itself.** The verification contract is owned by a seat outside the
  producing chain; if you collapse that, the audit is theatre.
- **Renaming a seat is cheap. Deleting one is not** — contracts reference owners (`E_CONTRACT`).

Change any of this and run `python -m governance.audit` before you commit.
