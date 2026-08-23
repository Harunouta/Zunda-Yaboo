"""Downsample a monthly JSONL into yearly-median series for Cursor canvases.

Writes logs/canvas_embed_<stem>.json (small). Does not call fetch. Engine untouched.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.purchasing_power import computePurchasingPower, foodYenPerCapita  # noqa: E402

YEAR_STEP = 5
KEY_YEARS = (1603, 1783, 1853, 1868, 1897, 1949, 2026)
ANOMALY_TABLE_LIMIT = 12
TOP_EVENTS_LIMIT = 10


def loadRows(path: Path) -> list[dict]:
  rows: list[dict] = []
  with path.open(encoding="utf-8") as handle:
    for line in handle:
      if line.strip():
        rows.append(json.loads(line))
  return rows


def medianOrZero(values: list[float]) -> float:
  if not values:
    return 0.0
  return round(float(statistics.median(values)), 4)


def yearOf(row: dict) -> int:
  yearMonth = str(row.get("yearMonth") or "")
  if yearMonth[:4].isdigit():
    return int(yearMonth[:4])
  return 0


def pppFromRow(row: dict, baselineFoodYen: float | None) -> dict:
  existing = row.get("purchasingPower") or {}
  if existing.get("foodYenPerCapita") is not None and existing.get("method") == "era_basket_times_grain_stock":
    return existing
  prices = row.get("prices") or {}
  macro = row.get("macro") or {}
  population = float(macro.get("population") or 1.0)
  food = float(macro.get("foodBuffer") or 0.0) / max(population, 1.0)
  year = yearOf(row) or 1603
  if baselineFoodYen is None:
    baselineFoodYen = foodYenPerCapita(food, year)
  live = computePurchasingPower(
    zundaPrice=float(prices.get("zundaPrice") or 1.0),
    ankoPrice=float(prices.get("ankoPrice") or 1.0),
    azukiPrice=float(prices.get("azukiPrice") or 0.0),
    ricePrice=float(prices.get("ricePrice") or 1.0),
    foodPerCapita=food,
    goldSilverRatio=float(macro.get("goldSilverRatio") or prices.get("goldPrice") or 1.0),
    baselineFoodYen=baselineFoodYen,
    year=year,
  )
  return live.toDict()


def yearlyBuckets(rows: list[dict]) -> dict:
  groups: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
  eventCounts: dict[str, int] = defaultdict(int)
  baseline: float | None = None
  firstYm = str(rows[0].get("yearMonth") or "")
  lastYm = str(rows[-1].get("yearMonth") or "")
  standards: dict[str, int] = defaultdict(int)

  for row in rows:
    year = yearOf(row)
    prices = row.get("prices") or {}
    fid = row.get("historicalFidelity") or {}
    macro = row.get("macro") or {}
    ppp = pppFromRow(row, baseline)
    if baseline is None:
      baseline = float(ppp.get("foodYenPerCapita") or 0.0) or None
    bucket = groups[year]
    bucket["zundaPrice"].append(float(prices.get("zundaPrice") or 0.0))
    bucket["ankoPrice"].append(float(prices.get("ankoPrice") or 0.0))
    bucket["azukiPrice"].append(float(prices.get("azukiPrice") or 0.0))
    bucket["ricePrice"].append(float(prices.get("ricePrice") or 0.0))
    bucket["fidelity"].append(float(fid.get("score") or 0.0))
    bucket["riceErr"].append(float(fid.get("riceErr") or 0.0))
    bucket["foodYen"].append(float(ppp.get("foodYenPerCapita") or 0.0))
    bucket["devIndex"].append(float(ppp.get("developmentIndex") or 0.0))
    bucket["livingPct"].append(float(ppp.get("livingVsModern") or 0.0) * 100.0)
    bucket["zundaYen"].append(float(ppp.get("zundaYen") or 0.0))
    bucket["ankoYen"].append(float(ppp.get("ankoYen") or 0.0))
    bucket["population"].append(float(macro.get("population") or 0.0))
    standards[str(row.get("monetaryStandard") or "?")] += 1
    for eventId in row.get("events") or []:
      if eventId != "riot_risk":
        eventCounts[str(eventId)] += 1

  yearsSorted = sorted(groups)
  sampledYears = [year for year in yearsSorted if year % YEAR_STEP == 0 or year in KEY_YEARS]
  if yearsSorted:
    if yearsSorted[0] not in sampledYears:
      sampledYears.insert(0, yearsSorted[0])
    if yearsSorted[-1] not in sampledYears:
      sampledYears.append(yearsSorted[-1])
  sampledYears = sorted(set(sampledYears))

  series = {
    "years": sampledYears,
    "zundaPrice": [medianOrZero(groups[y]["zundaPrice"]) for y in sampledYears],
    "ankoPrice": [medianOrZero(groups[y]["ankoPrice"]) for y in sampledYears],
    "azukiPrice": [medianOrZero(groups[y]["azukiPrice"]) for y in sampledYears],
    "ricePrice": [medianOrZero(groups[y]["ricePrice"]) for y in sampledYears],
    "fidelity": [medianOrZero(groups[y]["fidelity"]) for y in sampledYears],
    "riceErr": [medianOrZero(groups[y]["riceErr"]) for y in sampledYears],
    "foodYen": [medianOrZero(groups[y]["foodYen"]) for y in sampledYears],
    "devIndex": [medianOrZero(groups[y]["devIndex"]) for y in sampledYears],
    "livingPct": [medianOrZero(groups[y]["livingPct"]) for y in sampledYears],
    "zundaYen": [medianOrZero(groups[y]["zundaYen"]) for y in sampledYears],
    "ankoYen": [medianOrZero(groups[y]["ankoYen"]) for y in sampledYears],
    "population": [medianOrZero(groups[y]["population"]) for y in sampledYears],
  }

  snapshots = []
  for year in KEY_YEARS:
    if year not in groups:
      continue
    snapshots.append(
      {
        "year": year,
        "foodYen": medianOrZero(groups[year]["foodYen"]),
        "livingPct": medianOrZero(groups[year]["livingPct"]),
        "devIndex": medianOrZero(groups[year]["devIndex"]),
        "fidelity": medianOrZero(groups[year]["fidelity"]),
        "ricePrice": medianOrZero(groups[year]["ricePrice"]),
        "zundaPrice": medianOrZero(groups[year]["zundaPrice"]),
      }
    )

  topEvents = sorted(eventCounts.items(), key=lambda item: item[1], reverse=True)[:TOP_EVENTS_LIMIT]
  return {
    "source": firstYm,
    "method": "era_basket_times_grain_stock",
    "downsample": f"yearly median every {YEAR_STEP} years plus key years",
    "monthCount": len(rows),
    "range": [firstYm, lastYm],
    "standards": dict(standards),
    "series": series,
    "snapshots": snapshots,
    "topEvents": [{"id": eventId, "months": count} for eventId, count in topEvents],
  }


def loadAnomalies(path: Path) -> list[dict]:
  if not path.exists():
    sibling = path.with_name(path.stem + "_anomaly.json")
    if sibling.exists():
      path = sibling
    else:
      default = ROOT / "logs" / "anomaly_months.json"
      if not default.exists():
        return []
      path = default
  raw = json.loads(path.read_text(encoding="utf-8"))
  if isinstance(raw, dict):
    months = raw.get("months") or raw.get("anomalies") or raw.get("items") or []
  else:
    months = raw
  out: list[dict] = []
  for item in months:
    if isinstance(item, str):
      out.append({"yearMonth": item})
    elif isinstance(item, dict):
      out.append(item)
  return out[:ANOMALY_TABLE_LIMIT]


def main() -> int:
  parser = argparse.ArgumentParser(description="Export downsampled JSON for canvases")
  parser.add_argument("--log", type=Path, default=ROOT / "logs" / "runs" / "historical_1603_2026.jsonl")
  parser.add_argument("--out", type=Path, default=None)
  parser.add_argument("--anomalies", type=Path, default=None)
  args = parser.parse_args()
  logPath = args.log
  if not logPath.exists():
    print(f"missing {logPath}")
    return 1
  rows = loadRows(logPath)
  if not rows:
    print("empty log")
    return 1
  payload = yearlyBuckets(rows)
  payload["source"] = str(logPath).replace("\\", "/")
  anomalyPath = args.anomalies or ROOT / "logs" / "anomaly_months.json"
  payload["anomalies"] = loadAnomalies(anomalyPath)

  outPath = args.out or ROOT / "logs" / f"canvas_embed_{logPath.stem}.json"
  outPath.parent.mkdir(parents=True, exist_ok=True)
  outPath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
  print(f"wrote {outPath} years={len(payload['series']['years'])} months={payload['monthCount']}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
