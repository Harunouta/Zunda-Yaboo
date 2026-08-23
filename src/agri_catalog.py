"""CSV catalogs for agri/logistics agents, crop calendar, and transport routes."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
AGENTS_DIR = WORKSPACE / "data" / "agents"
KIT_PATH = WORKSPACE / "data" / "events" / "policies" / "kit_classes.csv"


@lru_cache(maxsize=1)
def loadAgriRoles() -> list[dict[str, str]]:
  path = AGENTS_DIR / "agri_roles.csv"
  with path.open(encoding="utf-8", newline="") as handle:
    return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def loadLogisticsRoutes() -> list[dict[str, str]]:
  path = AGENTS_DIR / "logistics_routes.csv"
  with path.open(encoding="utf-8", newline="") as handle:
    return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def loadCropCalendar() -> dict[int, dict[str, float]]:
  path = AGENTS_DIR / "crop_calendar.csv"
  byMonth: dict[int, dict[str, float]] = {}
  with path.open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
      month = int(row["month"])
      byMonth[month] = {
        key: float(row[key])
        for key in row
        if key != "month"
      }
  return byMonth


@lru_cache(maxsize=1)
def loadKitClasses() -> dict[str, dict[str, float]]:
  if not KIT_PATH.exists():
    return {}
  out: dict[str, dict[str, float]] = {}
  with KIT_PATH.open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
      kitId = str(row["kitId"])
      out[kitId] = {
        key: float(row[key])
        for key in row
        if key != "kitId"
      }
  return out


def reloadAgriCatalog() -> None:
  loadAgriRoles.cache_clear()
  loadLogisticsRoutes.cache_clear()
  loadCropCalendar.cache_clear()
  loadKitClasses.cache_clear()


def cropLabor(areaId: str, yearMonth: str) -> float:
  month = int(str(yearMonth).split("-")[1])
  table = loadCropCalendar()
  return float((table.get(month) or {}).get(areaId) or 1.0)


def openRoutesForMonth(yearMonth: str) -> list[dict[str, str]]:
  stamp = str(yearMonth)
  opened: list[dict[str, str]] = []
  for row in loadLogisticsRoutes():
    if str(row.get("openFrom") or "1603-01") <= stamp:
      opened.append(row)
  return opened


def routeMapsForMonth(yearMonth: str) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float]]:
  """Best (lowest) cost and best (highest) capacity per directed pair among open routes."""
  costs: dict[tuple[str, str], float] = {}
  caps: dict[tuple[str, str], float] = {}
  for row in openRoutesForMonth(yearMonth):
    pair = (str(row["fromArea"]), str(row["toArea"]))
    cost = float(row["baseCost"])
    cap = float(row["capacityRatio"])
    if pair not in costs or cost < costs[pair]:
      costs[pair] = cost
    if pair not in caps or cap > caps[pair]:
      caps[pair] = cap
  return costs, caps
