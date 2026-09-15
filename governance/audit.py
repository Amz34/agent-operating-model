"""Governed-fleet audit - validate a roles + planes + levels bundle before it ships.

Rules (each one is a real failure mode we hit while running an agent org):
  E_DUP_ID / E_ROSTER      seat ids must be unique and contiguous - every task needs one owner
  E_PLANE / E_LEVEL / E_COST   every seat must sit on a known plane, autonomy level and cost tier
  E_MANDATE                a mandate under 20 chars cannot be enforced
  E_EMPTY_PLANE / E_OWNER / E_SEAT_COUNT   a plane with no seat, or an owner off the roster, is unowned work
  E_CONTRACT               every contract must be owned by a seat that exists
  E_UNGUARDED              a plane granting L3+ must bind the verification + approvals contracts
  E_LADDER                 the escalation ladder is what makes L0 mean anything
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LEVEL_ORDER = ["L0", "L1", "L2", "L3", "L4"]
GOVERNED = {"verification", "approvals"}
PLANE_RE = re.compile(r"^P[0-7]$")
COST_TIERS = {f"T{i}" for i in range(5)}
HERE = Path(__file__).resolve().parent
DEFAULTS = {
    "roles": HERE.parent / "roles" / "roles.json",
    "planes": HERE.parent / "planes" / "planes.json",
    "levels": HERE / "levels.json",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit(roles_doc, planes_doc, levels_doc):
    """Return a list of (code, subject, detail) findings. Empty list == clean."""
    findings = []
    roles = roles_doc.get("roles", [])
    planes = {p["id"]: p for p in planes_doc.get("planes", [])}
    contracts = planes_doc.get("contract_layout", [])
    levels = {lvl["id"] for lvl in levels_doc.get("levels", [])}
    found = set()

    for role in roles:
        rid = role.get("id", "?")
        if rid in found:
            findings.append(("E_DUP_ID", rid, "seat id appears twice"))
        found.add(rid)
        if not PLANE_RE.match(str(role.get("plane", ""))):
            findings.append(("E_PLANE", rid, f"unknown plane {role.get('plane')!r}"))
        if role.get("autonomy") not in levels:
            findings.append(("E_LEVEL", rid, f"unknown autonomy {role.get('autonomy')!r}"))
        if role.get("cost_tier") not in COST_TIERS:
            findings.append(("E_COST", rid, f"unknown cost tier {role.get('cost_tier')!r}"))
        if len(str(role.get("mandate", ""))) < 20:
            findings.append(("E_MANDATE", rid, "mandate under 20 chars - unenforceable"))

    nums = sorted(int(x[1:]) for x in found if x.startswith("D") and x[1:].isdigit())
    if nums and nums != list(range(1, len(nums) + 1)):
        findings.append(("E_ROSTER", "roster", f"seat ids not contiguous: {len(nums)} seats, max {nums[-1]}"))

    for pid, plane in sorted(planes.items()):
        seats = [r for r in roles if r.get("plane") == pid]
        if not seats:
            findings.append(("E_EMPTY_PLANE", pid, "plane has no seat"))
        if plane.get("owner") and plane["owner"] not in found:
            findings.append(("E_OWNER", pid, f"owner {plane['owner']} is not on the roster"))
        if plane.get("seats") != len(seats):
            findings.append(("E_SEAT_COUNT", pid, f"declared {plane.get('seats')} seats, roster has {len(seats)}")) 

    for contract in contracts:
        if contract.get("owner") not in found:
            findings.append(("E_CONTRACT", str(contract.get("contract")), f"owner {contract.get('owner')} missing"))

    for pid, plane in sorted(planes.items()):
        risky = [r for r in roles
                 if r.get("plane") == pid and r.get("autonomy") in LEVEL_ORDER[3:]]
        missing = GOVERNED - set(plane.get("binds", []))
        if risky and missing:
            findings.append(("E_UNGUARDED", pid,
                             f"{len(risky)} seat(s) at L3+ but plane does not bind {', '.join(sorted(missing))}"))

    if not levels_doc.get("escalation_ladder"):
        findings.append(("E_LADDER", "levels", "escalation ladder missing"))

    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit an agent operating model before you ship it.")
    ap.add_argument("--roles", default=DEFAULTS["roles"])
    ap.add_argument("--planes", default=DEFAULTS["planes"])
    ap.add_argument("--levels", default=DEFAULTS["levels"])
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    args = ap.parse_args(argv)

    roles_doc, planes_doc, levels_doc = load(args.roles), load(args.planes), load(args.levels)
    findings = audit(roles_doc, planes_doc, levels_doc)
    seats = len(roles_doc.get("roles", []))
    planes = len(planes_doc.get("planes", []))

    if args.json:
        print(json.dumps({"seats": seats, "planes": planes, "findings": findings}, indent=2))
    else:
        print(f"audit: {seats} seats across {planes} planes")
        for code, subject, detail in findings:
            print(f"  {code:14} {subject:6} {detail}")
        print("result:", "clean" if not findings else f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
