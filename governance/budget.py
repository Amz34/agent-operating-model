"""Cost envelopes - a cost tier is a promise about spend, so check it.

roles.json declares a daily ceiling per tier; every seat inherits the ceiling of the tier it sits
on. Spend is passed in as {seat_id: usd_today}, so this stays a pure function: no clocks, no
network, no vendor SDK. Stdlib only.

    python -m governance.budget --spend '{"D7": 4.5, "D12": 0.2}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROLES = ROOT / "roles" / "roles.json"
E_UNKNOWN_SEAT = "E_UNKNOWN_SEAT"
E_NO_CEILING = "E_NO_CEILING"
E_OVER_BUDGET = "E_OVER_BUDGET"


def load(path):
    return json.loads(Path(path).read_text())


def envelope(roles_doc):
    """Per tier: the declared ceiling, the seats on it and their combined daily allowance."""
    budget = roles_doc.get("budget", {})
    out = {}
    for tier, ceiling in budget.items():
        seats = [s["id"] for s in roles_doc["roles"] if s.get("cost_tier") == tier]
        out[tier] = {"ceiling_usd_day": ceiling, "seats": len(seats), "seat_ids": seats,
                     "allowance_usd_day": round(ceiling * len(seats), 2) if ceiling else 0}
    return out


def spend_findings(roles_doc, spend):
    """Findings for one day of spend. Rule codes mirror governance/audit.py."""
    budget = roles_doc.get("budget", {})
    by_id = {s["id"]: s for s in roles_doc["roles"]}
    findings = []
    for seat_id, usd in sorted(spend.items()):
        seat = by_id.get(seat_id)
        if seat is None:
            findings.append({"code": E_UNKNOWN_SEAT, "seat": seat_id,
                             "detail": f"{usd} spent by a seat that is not on the roster"})
            continue
        ceiling = budget.get(seat["cost_tier"])
        if not ceiling and usd > 0:
            findings.append({"code": E_NO_CEILING, "seat": seat_id,
                             "detail": f"{usd} spent on {seat['cost_tier']}, which has no ceiling"})
        elif ceiling and usd > ceiling:
            findings.append({"code": E_OVER_BUDGET, "seat": seat_id,
                             "detail": f"{usd} > ceiling {ceiling} for {seat['cost_tier']}"})
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m governance.budget", description=__doc__)
    ap.add_argument("--spend", help="JSON map of seat_id to USD spent today")
    ap.add_argument("--roles", default=str(DEFAULT_ROLES))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    roles_doc = load(args.roles)
    spend = json.loads(args.spend) if args.spend else {}
    findings = spend_findings(roles_doc, spend)
    if args.json:
        print(json.dumps({"budget": envelope(roles_doc), "findings": findings}, indent=2))
    else:
        for tier, row in envelope(roles_doc).items():
            print(f"{tier}  ceiling {row['ceiling_usd_day']}/day x {row['seats']} seats"
                  f" = {row['allowance_usd_day']}/day")
        print(f"spend checked: {len(spend)} seats | findings: {len(findings)}")
        for f in findings:
            print(f"  {f['code']} {f['seat']}: {f['detail']}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
