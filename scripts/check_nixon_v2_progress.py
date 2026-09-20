#!/usr/bin/env python3
"""Print progress snapshot for v2 Nixon historical run."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS2_LOG = ROOT / "logs" / "runs" / "historical_1603_nixon_v2" / "monthly_pass2.jsonl"
PASS2_OUT = ROOT / "logs" / "runs" / "historical_1603_nixon_v2" / "run_pass2.out"
PASS3_LOG = ROOT / "logs" / "runs" / "historical_1603_nixon_v2" / "monthly_pass3.jsonl"
PASS3_OUT = ROOT / "logs" / "runs" / "historical_1603_nixon_v2" / "run_pass3.out"
PASS1_LOG = ROOT / "logs" / "runs" / "historical_1603_nixon_v2" / "monthly.jsonl"
PASS1_OUT = ROOT / "logs" / "runs" / "historical_1603_nixon_v2" / "run.out"
WANT = (
  "1603-01",
  "1721-01",
  "1872-01",
  "1920-10",
  "1945-08",
  "1960-10",
  "1970-10",
  "1971-08",
)


def main() -> None:
  if PASS3_LOG.is_file() and PASS3_LOG.stat().st_size > 0:
    logPath, outPath = PASS3_LOG, PASS3_OUT
  elif PASS2_LOG.is_file() and PASS2_LOG.stat().st_size > 0:
    logPath, outPath = PASS2_LOG, PASS2_OUT
  else:
    logPath, outPath = PASS1_LOG, PASS1_OUT
  print(f"=== using {logPath.name} / {outPath.name} ===")
  print("=== run.out tail ===")
  if outPath.is_file():
    lines = outPath.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-8:]:
      print(line)
  else:
    print("(no run.out yet)")

  if not logPath.is_file():
    print("monthly jsonl missing")
    return

  found: dict[str, tuple] = {}
  last = None
  count = 0
  with logPath.open(encoding="utf-8") as handle:
    for line in handle:
      if not line.strip():
        continue
      row = json.loads(line)
      count += 1
      last = row
      ym = row["yearMonth"]
      if ym in WANT:
        fid = row.get("historicalFidelity") or {}
        found[ym] = (
          round(float(row["macro"]["population"]), 1),
          (fid.get("target") or {}).get("populationMan"),
          fid.get("populationErr"),
          fid.get("score"),
          row.get("monetaryStandard"),
        )

  print(f"=== months={count} last={None if last is None else last.get('yearMonth')} ===")
  for ym in WANT:
    if ym not in found:
      continue
    pop, tgt, err, score, std = found[ym]
    print(f"{ym} std={std} pop={pop} tgt={tgt} popErr={err} fid={score}")


if __name__ == "__main__":
  main()
