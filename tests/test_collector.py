"""Telemetry contract tests: the ledger has to stay machine-readable and shareable."""
import json
from pathlib import Path

from telemetry import collector as C

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "telemetry" / "schema.json").read_text())["record"]


def test_record_matches_schema():
    rec = C.sample()
    for key in SCHEMA["required"]:
        assert key in rec, f"missing {key}"
    for key, kind in SCHEMA["types"].items():
        kinds = kind if isinstance(kind, list) else [kind]
        assert type(rec[key]).__name__ in kinds, f"{key} is {type(rec[key]).__name__}"
    for section in ("cpu", "mem", "disk", "procs"):
        for key in SCHEMA[f"{section}_keys"]:
            assert key in rec[section], f"missing {section}.{key}"


def test_redaction_is_the_default():
    assert "host" not in C.sample()
    assert C.sample(include_host=True)["host"]


def test_values_are_bounded():
    rec = C.sample()
    assert rec["cpu"]["cores"] >= 1
    assert rec["procs"]["total"] >= 1
    assert rec["procs"]["running"] <= rec["procs"]["total"]
    for pct in (rec["mem"]["used_pct"], rec["disk"]["used_pct"]):
        assert pct is None or 0 <= pct <= 100
    assert rec["sample_ms"] < 5000, "a sample slower than 5s cannot run every 30s"


def test_cli_writes_a_jsonl_ledger(tmp_path, capsys):
    ledger = tmp_path / "ledger.jsonl"
    assert C.main(["--append", str(ledger)]) == 0
    print_line = capsys.readouterr().out.strip()
    file_line = ledger.read_text().strip()
    assert json.loads(print_line) == json.loads(file_line)
    assert len(ledger.read_text().strip().splitlines()) == 1
