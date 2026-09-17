"""Task router - turn a task description into a seat, an autonomy level and a cost tier.

Deterministic on purpose: you must be able to predict, grep and unit-test which seat picks up a
task, otherwise the org chart is fiction. No model calls, no embeddings, no network.

    python -m governance.router "rotate the API key and tell the client"
    python -m governance.router --json --strict "rebuild the nightly search index"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROLES = ROOT / "roles" / "roles.json"
DEFAULT_PLANES = ROOT / "planes" / "planes.json"
ESCALATED = {"L3", "L4"}


def load(path):
    return json.loads(Path(path).read_text())


def _matches(needle, hay):
    """Whole-token match, tolerant of plurals and simple suffixes.

    Signals include two-letter tokens (`ui`, `ux`, `qa`, `bot`, `seo`). Plain substring matching
    let "build" contain `ui`, "both" contain `bot` and "auxiliary" contain `ux`, so ordinary task
    text routed to a specialist seat at medium confidence and the unrouted fallback never fired.
    Match only on token edges.
    """
    needle = needle.lower()
    tail = r"[a-z]{0,5}" if len(needle) >= 5 else r"s?"
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}{tail}(?![a-z0-9])", hay) is not None


def _score(text, seat):
    hay = text.lower()
    hits = [s for s in seat.get("signals", []) if _matches(s, hay)]
    heads = [w for w in str(seat.get("title", "")).lower().split() if len(w) > 3 and _matches(w, hay)]
    return len(hits) * 2 + len(heads), hits, heads


def _confidence(points, runner_up):
    if points >= 4 and points > runner_up:
        return "high"
    return "medium" if points >= 2 else "low"


def _plan(seat, matched, planes, confidence, runner_up, why, unrouted):
    plane = planes.get(seat["plane"], {})
    return {
        "seat": seat["id"],
        "title": seat["title"],
        "plane": seat["plane"],
        "autonomy": seat["autonomy"],
        "cost_tier": seat["cost_tier"],
        "matched": matched,
        "confidence": confidence,
        "runner_up_points": runner_up,
        "requires_approval": seat["autonomy"] in ESCALATED,
        "contracts": plane.get("binds", []),
        "why": why or ("matched " + ", ".join(matched)),
        "unrouted": unrouted,
    }


def route(text, roles_doc, planes_doc=None, fallback="D1"):
    """Map one task onto one accountable seat, or fail loudly when nothing matches."""
    planes = {p["id"]: p for p in (planes_doc or {}).get("planes", [])}
    ranked = []
    for seat in roles_doc["roles"]:
        points, hits, heads = _score(text, seat)
        if points:
            ranked.append({"points": points, "seat": seat, "matched": hits + heads})
    ranked.sort(key=lambda row: (-row["points"], row["seat"]["id"]))
    if not ranked:
        seat = next((s for s in roles_doc["roles"] if s["id"] == fallback), roles_doc["roles"][0])
        return _plan(seat, [], planes, "low", 0, "no signal matched - default triage seat", True)
    top = ranked[0]
    runner = ranked[1]["points"] if len(ranked) > 1 else 0
    return _plan(top["seat"], top["matched"], planes,
                 _confidence(top["points"], runner), runner, None, False)


def format_plan(plan):
    return "\n".join([
        f"{plan['seat']}  {plan['title']}",
        (f"  plane {plan['plane']} | autonomy {plan['autonomy']}"
         f" | cost {plan['cost_tier']} | confidence {plan['confidence']}"),
        (f"  approval: {'REQUIRED' if plan['requires_approval'] else 'not required'}"
         f" | contracts: {', '.join(plan['contracts']) or 'none'}"),
        f"  why: {plan['why']}",
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m governance.router", description=__doc__)
    parser.add_argument("task", help="the task in plain words")
    parser.add_argument("--roles", default=str(DEFAULT_ROLES))
    parser.add_argument("--planes", default=str(DEFAULT_PLANES))
    parser.add_argument("--fallback", default="D1")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit 1 when nothing matched")
    args = parser.parse_args(argv)
    plan = route(args.task, load(args.roles), load(args.planes), args.fallback)
    print(json.dumps(plan, indent=2) if args.json else format_plan(plan))
    return 1 if (args.strict and plan["unrouted"]) else 0


if __name__ == "__main__":
    sys.exit(main())
