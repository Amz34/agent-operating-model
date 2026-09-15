# Planes and the contract layout

A **plane** is a failure domain, not a team. When something breaks, the plane tells you which kind of
thing broke: the box (`P0`), the data (`P1`), the model (`P2`), the reasoning (`P3`), the authority
(`P4`), the org (`P5`), the interface (`P6`), or the demand (`P7`).

| Plane | Name | Owns |
|---|---|---|
| `P0` | COMPUTE | the machine, its limits, and everything that keeps it alive |
| `P1` | DATA | where truth is stored, shaped and made queryable |
| `P2` | MODEL | which intelligence is called, at what cost, with what fallback |
| `P3` | INTELLIGENCE | turning raw signal into decisions someone can act on |
| `P4` | GOVERNANCE | authority, autonomy envelopes, verification and security |
| `P5` | AGENT ORG | seats, mandates, handoffs and escalation |
| `P6` | INTERFACE | how humans reach the system and how it reports back |
| `P7` | GROWTH | demand, content, leads and everything revenue-facing |

## The contract layout

A contract is a **fleet-wide guarantee owned by a seat**, and planes *bind* the contracts they must
honour. Keeping ownership and binding separate is what makes the layout scale: five contracts cover
eight planes, and the auditor can check both directions.

```json
"contract_layout": [
  { "contract": "verification", "owner": "D12", "plane": "P4", "intent": "verdict on a different provider" },
  { "contract": "approvals",    "owner": "D21", "plane": "P4", "intent": "L3 queue, rollback path" }
],
"planes": [
  { "id": "P3", "name": "INTELLIGENCE", "owner": "D7", "seats": 4, "binds": ["approvals", "verification"] }
]
```

**The one rule to keep:** a plane granting `L3` or higher must bind both `verification` and
`approvals`. `governance/audit.py` refuses the model otherwise (`E_UNGUARDED`).

## Adding a plane

1. Add the plane to `planes.json` with an `owner` that is a real seat, a `seats` count, and `binds`.
2. Update that seat's `plane` field in `roles.json` — seats cannot drift between planes.
3. `python -m governance.audit` — `E_EMPTY_PLANE`, `E_OWNER` and `E_SEAT_COUNT` catch half-done moves.
