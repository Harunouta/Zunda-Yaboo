"""Monetary-regime switches (Edo metal → gold yen → yen FX regimes)."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from src.economy import MonetaryStandard, STOCK_SCALE, isYenFxStandard

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
  """Mutate economy.monetaryStandard. Seed yen fiat stocks on first yen-FX month."""
  wanted = standardForMonth(yearMonth)
  previous = economy.monetaryStandard
  if wanted == previous:
    return None
  economy.monetaryStandard = wanted
  enteringYenFx = isYenFxStandard(wanted) and not isYenFxStandard(previous)
  if enteringYenFx:
    if float(economy.dollarNotes or 0.0) < 100.0 * STOCK_SCALE:
      gold = max(float(economy.goldRyo or 0.0), 50.0)
      economy.dollarNotes = gold * 5.0
      economy.dollarReserves = gold * 3.5
  return f"{previous.value}->{wanted.value}"
