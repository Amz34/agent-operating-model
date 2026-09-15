import json

from telemetry import ledger
from telemetry.collector import sample


def test_append_and_read_round_trip(tmp_path):
    path = tmp_path / "ledger.jsonl"
    record = sample()
    ledger.append(path, record)
    assert ledger.read(path) == [record]
    assert path.read_text().count("\n") == 1


def test_tolerant_reader_skips_a_truncated_line(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text('{"ts": "a"}\n{"ts": "b"\n\n{"ts": "c"}\n')
    assert [r["ts"] for r in ledger.read(path)] == ["a", "c"]


def test_missing_ledger_reads_as_empty(tmp_path):
    assert ledger.read(tmp_path / "nope.jsonl") == []
    assert ledger.rollup([]) == {"samples": 0}


def test_rollup_reports_the_worst_case_and_the_window():
    records = [
        {"ts": "t1", "cpu": {"load_1": 1.0}, "mem": {"used_pct": 10.0},
         "disk": {"used_pct": 20.0}, "sample_ms": 8},
        {"ts": "t2", "cpu": {"load_1": 5.0}, "mem": {"used_pct": 40.0},
         "disk": {"used_pct": 60.0}, "sample_ms": 12},
    ]
    row = ledger.rollup(records)
    assert (row["samples"], row["first_ts"], row["last_ts"]) == (2, "t1", "t2")
    assert row["load_1"]["max"] == 5.0 and row["mem_used_pct"]["max"] == 40.0
    assert row["sample_ms"]["avg"] == 10.0


def test_alerts_fire_only_above_the_limit():
    quiet = {"cpu": {"load_1": 0.5}, "mem": {"used_pct": 10.0}, "disk": {"used_pct": 10.0}}
    hot = {"cpu": {"load_1": 9.0}, "mem": {"used_pct": 95.0}, "disk": {"used_pct": 91.0}}
    assert ledger.alerts(quiet) == []
    assert [m for m, _value, _limit in ledger.alerts(hot)] == ["load_1", "mem_used_pct", "disk_used_pct"]


def test_cli_appends_rolls_up_and_alerts(tmp_path, capsys):
    path = tmp_path / "ledger.jsonl"
    assert ledger.main(["--path", str(path), "--append", "--rollup", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["samples"] == 1
    assert ledger.main(["--path", str(path), "--alerts", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
