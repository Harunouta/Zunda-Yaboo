"""Historical reference track for edo_metal validity (history-following policy)."""

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
EARLY_MODERN_RICE_CSV = WORKSPACE / "data" / "early_modern" / "rice_price_index.csv"
EARLY_MODERN_RICE_BLEND = 0.5
RICE_BD_START = 1883
RICE_BD_END = 2022


@dataclass
class HistoricalMonthTarget:
  yearMonth: str
  riceIndex: float
  goldSilverRatio: float
  legitimacy: float
  populationIndex: float
  notes: str = ""

  def toDict(self) -> dict[str, Any]:
    return {
      "yearMonth": self.yearMonth,
      "riceIndex": self.riceIndex,
      "goldSilverRatio": self.goldSilverRatio,
      "legitimacy": self.legitimacy,
      "populationIndex": self.populationIndex,
      "notes": self.notes,
    }


# Sparse anchors; interpolated monthly for validity scoring.
HISTORICAL_ANCHORS: list[tuple[int, int, float, float, float, float, str]] = [
  # year, month, riceIndex, goldSilver, legitimacy, popIndex, note
  (1603, 1, 1.00, 1.00, 0.75, 1.00, "bakufu_founding"),
  (1615, 1, 1.05, 1.00, 0.78, 1.05, "osaka_fall"),
  (1651, 1, 1.10, 1.02, 0.72, 1.15, "keian"),
  (1709, 1, 1.20, 1.05, 0.70, 1.35, "shotoku"),
  (1783, 8, 1.80, 1.08, 0.55, 1.20, "tenmei"),
  (1836, 1, 1.70, 1.10, 0.50, 1.25, "tenpo"),
  (1853, 7, 1.40, 1.15, 0.48, 1.30, "perry"),
  (1858, 7, 1.55, 1.35, 0.42, 1.32, "harris_gold_outflow"),
  (1868, 1, 1.65, 1.40, 0.45, 1.35, "meiji"),
  (1890, 1, 1.20, 1.20, 0.60, 1.80, "modernizing"),
  (1923, 9, 1.50, 1.10, 0.55, 2.20, "kanto_eq"),
  (1945, 8, 2.50, 0.80, 0.25, 2.00, "war_end"),
  (1960, 1, 1.10, 1.00, 0.70, 3.00, "high_growth"),
  (1991, 1, 1.30, 1.05, 0.65, 3.50, "bubble"),
  (2011, 3, 1.25, 1.02, 0.60, 3.60, "tohoku"),
  (2020, 3, 1.15, 1.00, 0.58, 3.55, "covid"),
  (2026, 8, 1.20, 1.00, 0.60, 3.50, "present"),
]


def _toOrdinal(year: int, month: int) -> int:
  return year * 12 + (month - 1)


@lru_cache(maxsize=1)
def earlyModernRiceByYear(market: str = "edo") -> dict[int, float]:
  """BD overlay: Figshare yield-inverse 1883-2022 only. Sim fill is not loaded."""
  path = EARLY_MODERN_RICE_CSV
  if not path.is_file():
    return {}

  series: dict[int, float] = {}
  with path.open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
      if str(row.get("market") or "edo") != market:
        continue
      try:
        year = int(row["year"])
        if year < RICE_BD_START or year > RICE_BD_END:
          continue
        evidence = str(row.get("evidence") or "")
        note = str(row.get("sourceNote") or "")
        if evidence.startswith("inferred") or "sim ricePrice" in note:
          continue
        series[year] = float(row["riceIndex"])
      except (KeyError, TypeError, ValueError):
        continue
  return series


def interpolateYearlyIndex(series: dict[int, float], year: int) -> float | None:
  """Interpolate inside the observed span only; do not clamp outside it."""
  if not series:
    return None
  if year in series:
    return series[year]
  years = sorted(series)
  if year < years[0] or year > years[-1]:
    return None
  for index in range(1, len(years)):
    left = years[index - 1]
    right = years[index]
    if left <= year <= right:
      span = max(right - left, 1)
      t = (year - left) / span
      return series[left] + (series[right] - series[left]) * t
  return None


def blendRiceIndex(year: int, anchorRice: float) -> float:
  overlay = interpolateYearlyIndex(earlyModernRiceByYear(), year)
  if overlay is None:
    return anchorRice
  return (1.0 - EARLY_MODERN_RICE_BLEND) * anchorRice + EARLY_MODERN_RICE_BLEND * overlay


def getHistoricalTarget(year: int, month: int) -> HistoricalMonthTarget:
  ordinal = _toOrdinal(year, month)
  anchors = [
    (_toOrdinal(y, m), rice, gs, leg, pop, note, y, m)
    for y, m, rice, gs, leg, pop, note in HISTORICAL_ANCHORS
  ]
  if ordinal <= anchors[0][0]:
    _, rice, gs, leg, pop, note, y, m = anchors[0]
    return HistoricalMonthTarget(
      f"{year:04d}-{month:02d}", blendRiceIndex(year, rice), gs, leg, pop, note
    )
  if ordinal >= anchors[-1][0]:
    _, rice, gs, leg, pop, note, y, m = anchors[-1]
    return HistoricalMonthTarget(
      f"{year:04d}-{month:02d}", blendRiceIndex(year, rice), gs, leg, pop, note
    )

  for index in range(1, len(anchors)):
    left = anchors[index - 1]
    right = anchors[index]
    if left[0] <= ordinal <= right[0]:
      span = max(right[0] - left[0], 1)
      t = (ordinal - left[0]) / span
      return HistoricalMonthTarget(
        yearMonth=f"{year:04d}-{month:02d}",
        riceIndex=blendRiceIndex(year, left[1] + (right[1] - left[1]) * t),
        goldSilverRatio=left[2] + (right[2] - left[2]) * t,
        legitimacy=left[3] + (right[3] - left[3]) * t,
        populationIndex=left[4] + (right[4] - left[4]) * t,
        notes=right[5] if t > 0.5 else left[5],
      )
  _, rice, gs, leg, pop, note, _, _ = anchors[-1]
  return HistoricalMonthTarget(
    f"{year:04d}-{month:02d}", blendRiceIndex(year, rice), gs, leg, pop, note
  )


def historicalPolicyForMonth(year: int, month: int) -> dict[str, float | str]:
  """Conservative bakufu-like policy knobs that track history."""
  target = getHistoricalTarget(year, month)
  if year < 1700:
    taxRate = 0.10
  elif year < 1853:
    taxRate = 0.14
  elif year < 1871:
    taxRate = 0.11
  elif year < 1897:
    taxRate = 0.12
  elif year < 1949:
    taxRate = 0.11
  else:
    taxRate = 0.13

  reserve = 0.0
  if target.notes in ("tenmei", "tenpo", "war_end"):
    reserve = 0.2
    taxRate = min(taxRate, 0.08)

  trade = "closed"
  if year >= 1858:
    trade = "limited"
  if year >= 1868:
    trade = "open"

  sugar = 0.0
  if year >= 1853:
    sugar = 8.0
  if year >= 1949:
    sugar = 12.0

  goldTarget = 1.0 if year >= 1897 else target.goldSilverRatio

  return {
    "taxRate": taxRate,
    "processBeansRatio": 0.45 if year >= 1868 else 0.4,
    "reserveReleaseRatio": reserve,
    "investSugarImport": sugar,
    "tradeStance": trade,
    "goldSilverTargetRatio": goldTarget,
    "hanSatsuIssueRatio": 0.05 if year < 1871 else 0.0,
    "enforcementBudget": 22.0,
  }


def scoreHistoricalFidelity(
  simRiceProxy: float,
  simGoldSilver: float,
  simLegitimacy: float,
  simPopIndex: float,
  target: HistoricalMonthTarget,
) -> dict[str, Any]:
  riceRatio = max(simRiceProxy, 1e-6) / max(target.riceIndex, 1e-6)
  riceErr = min(abs(math.log(riceRatio)), 1.5)
  gsErr = abs(simGoldSilver - target.goldSilverRatio) / max(target.goldSilverRatio, 1e-6)
  legErr = abs(simLegitimacy - target.legitimacy)
  popErr = abs(simPopIndex - target.populationIndex) / max(target.populationIndex, 1e-6)
  # Weighted; lower error => higher score
  error = riceErr * 0.35 + gsErr * 0.25 + legErr * 0.2 + popErr * 0.2
  score = max(0.0, 1.0 - error)
  return {
    "score": round(score, 4),
    "riceErr": round(riceErr, 4),
    "goldSilverErr": round(gsErr, 4),
    "legitimacyErr": round(legErr, 4),
    "populationErr": round(popErr, 4),
    "target": target.toDict(),
  }
