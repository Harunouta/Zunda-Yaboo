#!/usr/bin/env python3
"""Snapshot population / regime / rates for 1970→2026 v2 run."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "runs" / "historical_1970_2026_v2" / "monthly.jsonl"
OUT = ROOT / "logs" / "runs" / "historical_1970_2026_v2" / "run.out"
WANT = (
  "1970-01",
  "1970-10",
  "1971-08",
  "1971-12",
  "1973-02",
  "1975-10",
  "1980-10",
  "1985-09",
  "1990-10",
  "2000-10",
  "2010-10",
  "2015-10",
  "2020-10",
  "2026-08",
)


def main() -> None:
  if OUT.is_file():
    print("=== run.out tail ===")
    for line in OUT.read_text(encoding="utf-8", errors="replace").splitlines()[-6:]:
      print(line)
  if not LOG.is_file():
    print("missing log")
    return
  found = {}
  last = None
  count = 0
  with LOG.open(encoding="utf-8") as handle:
    for line in handle:
      if not line.strip():
        continue
      row = json.loads(line)
      count += 1
      last = row
      ym = row["yearMonth"]
      if ym in WANT:
        fid = row.get("historicalFidelity") or {}
        found[ym] = row
  print(f"months={count} last={None if last is None else last.get('yearMonth')}")
  for ym in WANT:
    row = found.get(ym)
    if not row:
      continue
    fid = row.get("historicalFidelity") or {}
    rate = row.get("interestRate") or {}
    print(
      f"{ym} std={row.get('monetaryStandard')} fxRegime={(row.get('macro') or {}).get('fxRegime')} "
      f"pop={(row.get('macro') or {}).get('population')} tgt={(fid.get('target') or {}).get('populationMan')} "
      f"popErr={fid.get('populationErr')} fx={(row.get('macro') or {}).get('fxYenPerDollar')} "
      f"rate={rate.get('policyRateAnnualPct')} kind={rate.get('policyRateKind')} "
      f"fxInt={row.get('fxIntervention')}"
    )


if __name__ == "__main__":
  main()
