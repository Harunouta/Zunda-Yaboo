"""Load optional monthly climate series from CSV; fall back to procedural climate."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_CLIMATE_CSV = WORKSPACE / "data" / "processed" / "climate_monthly.csv"

# Blend weight when both series and procedural exist (1.0 = fully trust CSV).
SERIES_BLEND = 0.85


def _yearMonthKey(year: int, month: int) -> str:
  return f"{year:04d}-{month:02d}"


@lru_cache(maxsize=1)
def loadClimateSeries(path: str | None = None) -> dict[str, dict[str, Any]]:
  csvPath = Path(path) if path else DEFAULT_CLIMATE_CSV
  if not csvPath.exists():
    return {}
  rows: dict[str, dict[str, Any]] = {}
  with csvPath.open(encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    for raw in reader:
      key = str(raw.get("yearMonth") or "").strip()
      if not key:
        continue
      try:
        climateIndex = float(raw.get("climateIndex", 0.0))
      except (TypeError, ValueError):
        continue
      disasterRaw = raw.get("disasterMultiplier")
      disaster: float | None
      try:
        disaster = float(disasterRaw) if disasterRaw not in (None, "") else None
      except (TypeError, ValueError):
        disaster = None
      rows[key] = {
        "climateIndex": climateIndex,
        "disasterMultiplier": disaster,
        "source": str(raw.get("source") or csvPath.name),
        "notes": str(raw.get("notes") or ""),
      }
  return rows


def clearClimateCache() -> None:
  loadClimateSeries.cache_clear()


def lookupClimateSeries(year: int, month: int) -> dict[str, Any] | None:
  return loadClimateSeries().get(_yearMonthKey(year, month))


def blendClimate(
  proceduralIndex: float,
  proceduralDisaster: float,
  seriesRow: dict[str, Any] | None,
  eventDisaster: float | None,
  blend: float = SERIES_BLEND,
) -> tuple[float, float, str]:
  """Return climateIndex, disasterMultiplier, sourceLabel."""
  if seriesRow is None:
    disaster = proceduralDisaster
    if eventDisaster is not None:
      disaster = min(disaster, eventDisaster)
    return proceduralIndex, max(min(disaster, 1.0), 0.2), "procedural"

  seriesIndex = float(seriesRow["climateIndex"])
  climateIndex = (1.0 - blend) * proceduralIndex + blend * seriesIndex
  seriesDisaster = seriesRow.get("disasterMultiplier")
  if seriesDisaster is None:
    disaster = 1.0 + min(climateIndex, 0.0)
  else:
    disaster = float(seriesDisaster)
  if eventDisaster is not None:
    disaster = min(disaster, eventDisaster)
  source = f"series:{seriesRow.get('source', 'csv')}"
  return climateIndex, max(min(disaster, 1.0), 0.2), source
