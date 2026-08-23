"""Regime lookup and gold_yen smoke."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.dollar_fx import fxYenPerDollar
from src.economy import EconomyState, MonetaryStandard
from src.historical_track import earlyModernRiceByYear
from src.monetary_regimes import applyRegimeSwitch, standardForMonth


def main() -> int:
  assert standardForMonth("1603-01") == MonetaryStandard.EDO_METAL
  assert standardForMonth("1897-10") == MonetaryStandard.GOLD_YEN
  assert standardForMonth("1949-04") == MonetaryStandard.DOLLAR
  assert standardForMonth("2026-08") == MonetaryStandard.DOLLAR
  economy = EconomyState(year=1897, month=9, monetaryStandard=MonetaryStandard.EDO_METAL, goldRyo=200.0)
  changed = applyRegimeSwitch(economy, "1897-10")
  assert changed == "edo_metal->gold_yen"
  economy2 = EconomyState(year=1949, month=3, monetaryStandard=MonetaryStandard.GOLD_YEN, goldRyo=200.0)
  applyRegimeSwitch(economy2, "1949-04")
  assert economy2.monetaryStandard == MonetaryStandard.DOLLAR
  assert economy2.dollarNotes > 100
  assert abs(fxYenPerDollar(1949, 4) - 360.0) < 0.01
  assert fxYenPerDollar(2026, 8) < 200
  riceYears = earlyModernRiceByYear()
  assert 1603 not in riceYears
  assert 1993 in riceYears
  print("test_regimes: OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
