import json
from pathlib import Path

from governance.router import format_plan, main, route

ROOT = Path(__file__).resolve().parents[1]
ROLES = json.loads((ROOT / "roles" / "roles.json").read_text())
PLANES = json.loads((ROOT / "planes" / "planes.json").read_text())


def test_routes_to_a_real_seat_with_a_real_level():
    plan = route("deploy the new release and rotate the credentials", ROLES, PLANES)
    assert plan["seat"].startswith("D")
    assert plan["autonomy"] in {"L0", "L1", "L2", "L3", "L4"}
    assert plan["confidence"] in {"low", "medium", "high"}
    assert plan["requires_approval"] == (plan["autonomy"] in {"L3", "L4"})


def test_router_never_invents_a_seat():
    plan = route("zzzq qqqw vvvu", ROLES, PLANES)
    assert plan["unrouted"] is True
    assert plan["seat"] == "D1"
    assert plan["matched"] == []


def test_contracts_follow_the_plane_of_the_chosen_seat():
    plan = route("security review of the new endpoint", ROLES, PLANES)
    plane = next(p for p in PLANES["planes"] if p["id"] == plan["plane"])
    assert plan["contracts"] == plane.get("binds", [])


def test_a_runaway_seat_always_carries_the_approval_gate():
    doc = {"roles": [{"id": "D1", "title": "Bot", "plane": "P0", "autonomy": "L4",
                      "cost_tier": "T0", "signals": ["deploy"]}]}
    plan = route("deploy now", doc, {"planes": [{"id": "P0", "binds": ["approvals"]}]})
    assert plan["requires_approval"] is True
    assert plan["contracts"] == ["approvals"]


def test_cli_plan_json_and_strict_exit_code(capsys):
    assert main(["rotate the api key"]) == 0
    out = capsys.readouterr().out
    assert "plane P" in out and "approval:" in out
    assert main(["--json", "rotate the api key"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["seat"] and payload["why"]
    assert main(["--strict", "zzzq qqqw vvvu"]) == 1
    assert "D1" in format_plan(route("zzzq qqqw vvvu", ROLES, PLANES))


def test_short_signals_never_match_inside_unrelated_words():
    # `ui` hides inside "build", `bot` inside "both", `ux` inside "auxiliary".
    for text in ("queue the build", "do both of them", "auxiliary cable"):
        plan = route(text, ROLES, PLANES)
        assert not {"ui", "ux", "bot"} & set(plan["matched"])


def test_gibberish_containing_a_short_signal_still_falls_back():
    plan = route("xyzzy plugh frobnicate quux", ROLES, PLANES)
    assert plan["unrouted"] is True
    assert plan["seat"] == "D1"
    assert plan["matched"] == []


def test_real_two_letter_signals_still_match_on_token_edges():
    assert route("build the ui for the client dashboard", ROLES, PLANES)["seat"] == "D10"
    assert "qa" in route("run the qa pass before release", ROLES, PLANES)["matched"]


def test_the_readme_example_routes_exactly_as_documented():
    plan = route("rotate the API key and tell the client", ROLES, PLANES)
    assert (plan["seat"], plan["confidence"], plan["matched"]) == ("D3", "low", ["client"])
    assert plan["requires_approval"] is False
