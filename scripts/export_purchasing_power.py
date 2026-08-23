"""Export modern-yen purchasing-power series from a monthly JSONL run."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.purchasing_power import (
  MODERN_FOOD_YEN_PER_CAPITA_MONTH,
  YEN_PER_KG_RICE,
  computePurchasingPower,
  foodYenPerCapita,
  summarizeEra,
)


def loadRows(path: Path) -> list[dict]:
  return [
    json.loads(line)
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip()
  ]


def enrichMonthly(rows: list[dict]) -> list[dict]:
  baseline: float | None = None
  out: list[dict] = []
  for row in rows:
    prices = row.get("prices") or {}
    macro = row.get("macro") or {}
    population = float(macro.get("population") or 0.0)
    foodBuffer = float(macro.get("foodBuffer") or 0.0)
    yearMonth = str(row.get("yearMonth") or "")
    year = int(str(yearMonth)[:4]) if str(yearMonth)[:4].isdigit() else 1603
    food = foodBuffer / max(population, 1.0)
    if baseline is None:
      baseline = foodYenPerCapita(food, year)
    pp = computePurchasingPower(
      zundaPrice=float(prices.get("zundaPrice") or 1.0),
      ankoPrice=float(prices.get("ankoPrice") or 1.0),
      ricePrice=float(prices.get("ricePrice") or 1.0),
      foodPerCapita=food,
      goldSilverRatio=float(macro.get("goldSilverRatio") or prices.get("goldPrice") or 1.0),
      baselineFoodYen=baseline,
      year=year,
    )
    payload = pp.toDict()
    out.append(
      {
        "yearMonth": row.get("yearMonth"),
        "standard": row.get("monetaryStandard"),
        "zundaPrice": prices.get("zundaPrice"),
        "ankoPrice": prices.get("ankoPrice"),
        "ricePrice": prices.get("ricePrice"),
        **payload,
        "livingVsModernPct": round(pp.livingVsModern * 100.0, 4),
      }
    )
  return out


def writeCsv(path: Path, rows: list[dict]) -> None:
  if not rows:
    raise SystemExit("no rows to export")
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
  parser = argparse.ArgumentParser(description="Export modern-yen PPP metrics from a run log")
  parser.add_argument(
    "--log",
    type=Path,
    default=Path("logs/runs/zunda_full_1603_2026.jsonl"),
  )
  parser.add_argument(
    "--out",
    type=Path,
    default=None,
    help="Monthly CSV path (default: <log>_ppp.csv)",
  )
  parser.add_argument(
    "--yearly-out",
    type=Path,
    default=None,
    help="Yearly summary CSV (default: <log>_ppp_yearly.csv)",
  )
  parser.add_argument(
    "--json-out",
    type=Path,
    default=None,
    help="Optional yearly JSON for Canvas embedding",
  )
  args = parser.parse_args()

  rows = loadRows(args.log)
  monthly = enrichMonthly(rows)
  yearly = summarizeEra(rows)

  outMonthly = args.out or args.log.with_name(args.log.stem + "_ppp.csv")
  outYearly = args.yearly_out or args.log.with_name(args.log.stem + "_ppp_yearly.csv")
  writeCsv(outMonthly, monthly)
  writeCsv(outYearly, yearly)

  if args.json_out:
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
      "source": str(args.log).replace("\\", "/"),
      "method": "era_basket_times_grain_stock",
      "yenPerKgRice": YEN_PER_KG_RICE,
      "modernFoodYenPerCapitaMonth": MODERN_FOOD_YEN_PER_CAPITA_MONTH,
      "yearly": yearly,
    }
    args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

  first = yearly[0]
  last = yearly[-1]
  print(
    f"months={len(monthly)} years={len(yearly)} "
    f"out={outMonthly} yearly={outYearly}"
  )
  print(
    f"start {first['year']}: food¥{first['foodYenPerCapita']} "
    f"live={first['livingVsModernPct']}% {first['vibe']}"
  )
  print(
    f"end   {last['year']}: food¥{last['foodYenPerCapita']} "
    f"live={last['livingVsModernPct']}% dev×{last['developmentIndex']} {last['vibe']}"
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
