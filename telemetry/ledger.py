"""Append-only telemetry ledger: JSONL samples, rollups and threshold alerts.

The collector answers "how is the box right now". The ledger answers "has it been getting worse",
which is the question you actually ask at 2am. Stdlib only; the file format is one JSON object per
line so it survives partial writes and can be tailed, grepped and shipped anywhere.

    python -m telemetry.ledger --path ledger.jsonl --rollup
    python -m telemetry.ledger --path ledger.jsonl --append
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from telemetry.collector import sample

DEFAULT_THRESHOLDS = {"load_1": 4.0, "mem_used_pct": 90.0, "disk_used_pct": 90.0}
DEFAULT_PATH = "ledger.jsonl"


def append(path, record):
    """Append one record. O_APPEND keeps concurrent writers from interleaving lines."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return target


def read(path):
    """Tolerant reader: a truncated last line is skipped, never fatal."""
    target = Path(path)
    if not target.exists():
        return []
    records = []
    for line in target.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


def _num(value):
    """Metrics are missing on platforms without /proc; that must never become a crash."""
    return value if isinstance(value, (int, float)) else None


def _load(record):
    return _num(record.get("cpu", {}).get("load_1"))


def _pct(record, key):
    return _num(record.get(key, {}).get("used_pct"))


def _spread(values):
    seen = [v for v in values if v is not None]
    if not seen:
        return {"max": None, "avg": None}
    return {"max": max(seen), "avg": round(sum(seen) / len(seen), 2)}


def rollup(records):
    """Trend view over a ledger: how many samples, over what window, and the worst seen.

    A metric the host cannot report stays null instead of poisoning the whole rollup.
    """
    if not records:
        return {"samples": 0}
    return {
        "samples": len(records),
        "first_ts": records[0].get("ts"),
        "last_ts": records[-1].get("ts"),
        "load_1": _spread([_load(r) for r in records]),
        "mem_used_pct": _spread([_pct(r, "mem") for r in records]),
        "disk_used_pct": _spread([_pct(r, "disk") for r in records]),
        "sample_ms": _spread([r.get("sample_ms") for r in records]),
    }


def alerts(record, thresholds=None):
    """Threshold breaches for one sample, as (metric, value, limit) triples."""
    limits = dict(DEFAULT_THRESHOLDS)
    limits.update(thresholds or {})
    observed = {"load_1": _load(record), "mem_used_pct": _pct(record, "mem"),
                "disk_used_pct": _pct(record, "disk")}
    return [(metric, value, limits[metric]) for metric, value in observed.items()
            if metric in limits and value is not None and value > limits[metric]]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m telemetry.ledger", description=__doc__)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--append", action="store_true", help="sample the box once, append it")
    parser.add_argument("--rollup", action="store_true", help="print the trend summary")
    parser.add_argument("--alerts", action="store_true", help="print threshold breaches")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.append:
        append(args.path, sample())
    records = read(args.path)
    if args.alerts:
        breaches = [b for r in records[-50:] for b in alerts(r)]
        if args.json:
            print(json.dumps([{"metric": m, "value": v, "limit": lim}
                              for m, v, lim in breaches], indent=2))
        else:
            print("\n".join(f"{m} {v} > {lim}" for m, v, lim in breaches) or "no breaches")
        return 1 if breaches else 0
    summary = rollup(records)
    print(json.dumps(summary, indent=2) if args.json else summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
