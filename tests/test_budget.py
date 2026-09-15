import json
from pathlib import Path

from governance.budget import (
    E_NO_CEILING,
    E_OVER_BUDGET,
    E_UNKNOWN_SEAT,
    envelope,
    main,
    spend_findings,
)

ROOT = Path(__file__).resolve().parents[1]
ROLES = json.loads((ROOT / "roles" / "roles.json").read_text())


def codes(findings):
    return [f["code"] for f in findings]


def test_every_tier_in_use_declares_a_ceiling():
    env = envelope(ROLES)
    assert set(env) == set(ROLES["budget"])
    assert sum(row["seats"] for row in env.values()) == len(ROLES["roles"])
    assert all(row["ceiling_usd_day"] >= 0 for row in env.values())


def test_spend_within_the_ceiling_is_clean():
    seat = ROLES["roles"][0]
    assert spend_findings(ROLES, {seat["id"]: 0}) == []


def test_over_budget_and_unknown_seat_are_both_caught():
    costly = next(s for s in ROLES["roles"] if ROLES["budget"][s["cost_tier"]] > 0)
    ceiling = ROLES["budget"][costly["cost_tier"]]
    found = spend_findings(ROLES, {costly["id"]: ceiling + 1, "D999": 2})
    assert codes(found) == [E_OVER_BUDGET, E_UNKNOWN_SEAT]


def test_a_tier_without_a_ceiling_is_flagged():
    doc = {"budget": {"T0": 0}, "roles": [{"id": "D1", "cost_tier": "T0"}]}
    assert codes(spend_findings(doc, {"D1": 0.5})) == [E_NO_CEILING]


def test_cli_exit_codes_and_json(capsys):
    quiet = ROLES["roles"][0]
    costly = next(s for s in ROLES["roles"] if ROLES["budget"][s["cost_tier"]] > 0)
    assert main(["--spend", json.dumps({quiet["id"]: 0})]) == 0
    assert main(["--spend", json.dumps({costly["id"]: 99})]) == 1
    capsys.readouterr()
    assert main(["--json"]) == 0
    assert "budget" in json.loads(capsys.readouterr().out)
