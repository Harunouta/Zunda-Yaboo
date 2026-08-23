"""Historical monetary-regime switches (Edo metal → gold yen → dollar)."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from src.economy import MonetaryStandard

WORKSPACE = Path(__file__).resolve().parents[1]
REGIME_PATH = WORKSPACE / "data" / "economy" / "monetary_regimes.csv"


@lru_cache(maxsize=1)
def loadRegimes() -> list[dict[str, str]]:
  with REGIME_PATH.open(encoding="utf-8", newline="") as handle:
    return list(csv.DictReader(handle))


def standardForMonth(yearMonth: str) -> MonetaryStandard:
  stamp = str(yearMonth)
  chosen = MonetaryStandard.EDO_METAL
  for row in loadRegimes():
    if str(row["fromMonth"]) <= stamp <= str(row["toMonth"]):
      chosen = MonetaryStandard(row["standard"])
  return chosen


def applyRegimeSwitch(economy, yearMonth: str) -> str | None:
  """Mutate economy.monetaryStandard. Seed dollar stocks on first Dodge month."""
  wanted = standardForMonth(yearMonth)
  previous = economy.monetaryStandard
  if wanted == previous:
    return None
  economy.monetaryStandard = wanted
  if wanted == MonetaryStandard.DOLLAR and previous != MonetaryStandard.DOLLAR:
    if float(economy.dollarNotes or 0.0) < 100.0:
      gold = max(float(economy.goldRyo or 0.0), 50.0)
      economy.dollarNotes = gold * 5.0
      economy.dollarReserves = gold * 3.5
  return f"{previous.value}->{wanted.value}"
