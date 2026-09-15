"""Designation-level telemetry sampler - standard library only, redaction-first.

Why it exists: you cannot run autonomy levels you cannot measure. This samples the
things a governed fleet must see before it decides to trust itself - load, memory,
disk, process pressure, uptime - as one flat JSON record per tick, cheap enough to
run every 30s on a free-tier box.

    python -m telemetry.collector                 # one sample
    python -m telemetry.collector --watch 30      # stream every 30s
    python -m telemetry.collector --append ledger.jsonl --watch 60
    python -m telemetry.collector --include-hostname   # opt-in, off by default
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import time
from pathlib import Path


def _read(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return default


def _meminfo():
    out = {}
    for line in _read("/proc/meminfo").splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts:
            out[key] = int(parts[0])
    return out


def sample(include_host=False):
    """One telemetry record. Never raises: a missing counter degrades to None."""
    started = time.time()
    load = (_read("/proc/loadavg").split() + [None, None, None])[:3]
    mem = _meminfo()
    uptime = _read("/proc/uptime").split()
    total_mb = mem.get("MemTotal", 0) / 1024
    avail_mb = mem.get("MemAvailable", mem.get("MemFree", 0)) / 1024

    procs = running = 0
    for entry in Path("/proc").iterdir() if Path("/proc").is_dir() else []:
        if not entry.name.isdigit():
            continue
        procs += 1
        stat = _read(entry / "stat")
        tail = stat.split(") ", 1)[1] if ") " in stat else ""
        if tail[:1] == "R":
            running += 1

    st = os.statvfs("/")
    disk_total = st.f_blocks * st.f_frsize / 2**30
    disk_used = (st.f_blocks - st.f_bfree) * st.f_frsize / 2**30

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cpu": {
            "cores": os.cpu_count(),
            "load_1": round(float(load[0]), 2) if load[0] else None,
            "load_5": round(float(load[1]), 2) if load[1] else None,
            "load_15": round(float(load[2]), 2) if load[2] else None,
        },
        "mem": {
            "total_mb": round(total_mb),
            "avail_mb": round(avail_mb),
            "used_pct": round((total_mb - avail_mb) / total_mb * 100, 1) if total_mb else None,
        },
        "disk": {
            "total_gb": round(disk_total, 1),
            "used_pct": round(disk_used / disk_total * 100, 1) if disk_total else None,
        },
        "procs": {"total": procs, "running": running},
        "uptime_s": int(float(uptime[0])) if uptime else None,
        "arch": platform.machine(),
    }
    if include_host:
        record["host"] = socket.gethostname()
    record["sample_ms"] = round((time.time() - started) * 1000, 1)
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sample fleet telemetry as flat JSON records.")
    ap.add_argument("--watch", type=float, metavar="SECONDS", help="keep sampling on this interval")
    ap.add_argument("--append", metavar="FILE", help="also append each record to a JSONL ledger")
    ap.add_argument("--include-hostname", action="store_true", help="include hostname (off by default)")
    args = ap.parse_args(argv)

    def emit():
        line = json.dumps(sample(args.include_hostname), ensure_ascii=False)
        print(line, flush=True)
        if args.append:
            with open(args.append, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    if not args.watch:
        emit()
        return 0
    while True:
        emit()
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
