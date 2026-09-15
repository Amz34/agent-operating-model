"""The audit is the product: a model you cannot check is a model you cannot trust."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from governance import audit as A

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle():
    def load(name):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))

    return load("roles/roles.json"), load("planes/planes.json"), load("governance/levels.json")


def codes(findings):
    return {code for code, _, _ in findings}


def test_shipped_model_is_clean(bundle):
    """The roster we publish must pass the rules we publish."""
    assert A.audit(*bundle) == []


def test_model_shape(bundle):
    roles, planes, levels = bundle
    assert roles["fleet"]["seats"] == 24 == len(roles["roles"])
    assert len(planes["planes"]) == 8
    assert len(levels["levels"]) == 5
    assert planes["contract_layout"], "contract layout is the whole point"
    assert {r["plane"] for r in roles["roles"]} == {p["id"] for p in planes["planes"]}


def test_duplicate_seat_id(bundle):
    roles, planes, levels = deepcopy(bundle)
    roles["roles"][1]["id"] = roles["roles"][0]["id"]
    assert "E_DUP_ID" in codes(A.audit(roles, planes, levels))


def test_unknown_plane_level_and_cost(bundle):
    roles, planes, levels = deepcopy(bundle)
    roles["roles"][0].update(plane="P9", autonomy="L7", cost_tier="T9")
    found = codes(A.audit(roles, planes, levels))
    assert {"E_PLANE", "E_LEVEL", "E_COST"} <= found


def test_thin_mandate(bundle):
    roles, planes, levels = deepcopy(bundle)
    roles["roles"][2]["mandate"] = "helps out"
    assert "E_MANDATE" in codes(A.audit(roles, planes, levels))


def test_roster_gap(bundle):
    roles, planes, levels = deepcopy(bundle)
    roles["roles"].pop(11)  # a gap in the middle is not a short roster
    assert "E_ROSTER" in codes(A.audit(roles, planes, levels))


def test_empty_plane_and_orphan_owner(bundle):
    roles, planes, levels = deepcopy(bundle)
    pid = planes["planes"][0]["id"]
    roles["roles"] = [r for r in roles["roles"] if r["plane"] != pid]
    planes["planes"][0]["owner"] = "D99"
    found = codes(A.audit(roles, planes, levels))
    assert {"E_EMPTY_PLANE", "E_OWNER"} <= found


def test_contract_needs_a_living_owner(bundle):
    roles, planes, levels = deepcopy(bundle)
    planes["contract_layout"][0]["owner"] = "D99"
    assert "E_CONTRACT" in codes(A.audit(roles, planes, levels))


def test_l3_plus_seat_on_unguarded_plane_is_blocked(bundle):
    """Autonomy above L2 on a plane that binds no guardrail contract is the failure we refuse."""
    roles, planes, levels = deepcopy(bundle)
    seat = roles["roles"][0]
    seat["autonomy"] = "L3"
    for plane in planes["planes"]:
        if plane["id"] == seat["plane"]:
            plane["binds"] = []
    assert "E_UNGUARDED" in codes(A.audit(roles, planes, levels))


def test_ladder_is_mandatory(bundle):
    roles, planes, levels = deepcopy(bundle)
    levels["escalation_ladder"] = []
    assert "E_LADDER" in codes(A.audit(roles, planes, levels))


def test_cli_exit_codes_and_json(bundle, capsys):
    assert A.main([]) == 0
    assert "result: clean" in capsys.readouterr().out
    assert A.main(["--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["findings"] == [] and out["seats"] == 24 and out["planes"] == 8
