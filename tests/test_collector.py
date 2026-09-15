"""Telemetry contract tests: the ledger has to stay machine-readable and shareable."""
import json
import sys
from pathlib import Path

import pytest

from telemetry import collector as C

LINUX = pytest.mark.skipif(sys.platform != "linux", reason="reads /proc, Linux only")

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "telemetry" / "schema.json").read_text())["record"]


def _kind(value):
    """None is null in the schema, not NoneType in the interpreter."""
    return "null" if value is None else type(value).__name__


def test_record_matches_schema():
    rec = C.sample()
    for key in SCHEMA["required"]:
        assert key in rec, f"missing {key}"
    for key, kind in SCHEMA["types"].items():
        kinds = kind if isinstance(kind, list) else [kind]
        assert _kind(rec[key]) in kinds, f"{key} is {_kind(rec[key])}"
    for section in ("cpu", "mem", "disk", "procs"):
        for key in SCHEMA[f"{section}_keys"]:
            assert key in rec[section], f"missing {section}.{key}"


def test_redaction_is_the_default():
    assert "host" not in C.sample()
    assert C.sample(include_host=True)["host"]


def test_values_are_bounded():
    rec = C.sample()
    assert rec["cpu"]["cores"] >= 1
    for pct in (rec["mem"]["used_pct"], rec["disk"]["used_pct"]):
        assert pct is None or 0 <= pct <= 100
    assert rec["sample_ms"] < 5000, "a sample slower than 5s cannot run every 30s"


@LINUX
def test_live_counters_on_linux():
    rec = C.sample()
    assert rec["procs"]["total"] >= 1
    assert rec["procs"]["running"] <= rec["procs"]["total"]
    assert rec["mem"]["used_pct"] is not None and rec["cpu"]["load_1"] is not None


def test_cli_writes_a_jsonl_ledger(tmp_path, capsys):
    ledger = tmp_path / "ledger.jsonl"
    assert C.main(["--append", str(ledger)]) == 0
    print_line = capsys.readouterr().out.strip()
    file_line = ledger.read_text().strip()
    assert json.loads(print_line) == json.loads(file_line)
    assert len(ledger.read_text().strip().splitlines()) == 1
