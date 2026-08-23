"""Smoke the dollar standard (implementation only, no modern CPI fit)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dollar_fx import fxYenPerDollar  # noqa: E402
from src.monthly_engine import runMonthlySimulation  # noqa: E402

LOG = ROOT / "logs" / "runs" / "smoke_dollar_2020_2021.jsonl"


def main() -> int:
  assert abs(fxYenPerDollar(1949, 4) - 360.0) < 0.01
  assert fxYenPerDollar(2024, 7) > 140.0
  runMonthlySimulation(
    standard="dollar",
    start="2020-01",
    end="2021-12",
    useLlm=False,
    resume=False,
    historicalPolicy=False,
    logPath=LOG,
    opinionLeaderCount=0,
    opinionParallel=False,
  )
  rows = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
  assert len(rows) == 24
  first = rows[0]
  last = rows[-1]
  assert first.get("monetaryStandard") == "dollar"
  assert (first.get("macro") or {}).get("dollarNotes", 0) > 0
  assert (first.get("purchasingPower") or {}).get("fxYenPerDollar", 0) > 100
  assert (last.get("prices") or {}).get("dollarPrice", 0) > 0
  print(
    "smoke_dollar: OK",
    "fx", (last.get("purchasingPower") or {}).get("fxYenPerDollar"),
    "dollarYen", (last.get("purchasingPower") or {}).get("dollarYen"),
    "notes", (last.get("macro") or {}).get("dollarNotes"),
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
