# Changelog

## 0.2.1

- **Fixed** `governance/router.py` — signals and title words now match on token edges instead of
  as bare substrings. Two-letter signals (`ui`, `ux`, `qa`, `bot`) used to fire inside unrelated
  words, so `"queue the build"` routed to the Front-end seat on the `ui` in *build*, and gibberish
  containing `ux` could never fall back to triage. Four regression tests added; the false-positive
  cases and the documented example are now pinned by tests.
- **Docs** test count refreshed (33 -> 37) and the routing row in the README says what the added
  tests actually guard.

## 0.2.0

- **Added** `governance/router.py` — deterministic task-to-seat routing with the approval gate and
  the plane contracts attached (`aom-route`, `--json`, `--strict`).
- **Added** `governance/budget.py` — per-tier cost envelopes and spend findings
  (`E_UNKNOWN_SEAT`, `E_NO_CEILING`, `E_OVER_BUDGET`) so cost tiers stop being decoration.
- **Added** `telemetry/ledger.py` — append-only JSONL ledger with trend rollups and threshold
  alerts, so "how is the box now" becomes "has it been getting worse".
- **Added** `E_SCHEMA` and `E_NO_BUDGET` audit rules; `roles.json` and `planes.json` now declare
  `schema_version` and `roles.json` declares a `budget` envelope per tier.
- **Added** `pyproject.toml` with console entry points, `docs/design.md`, and a changelog.
- **Changed** CI: ruff, coverage, a 3-OS matrix and a packaging smoke test.

## 0.1.0

- First release: 24 seat specifications, 8 planes, 5 contract assignments, the L0-L4 autonomy
  ladder, `governance/audit.py` and `telemetry/collector.py` (15 tests).
