"""Rebuild rice BD series: Figshare yield inverse only (1883-2022).

Default does not write sim fill. Use --fill-sim for the archived inferred file.
"""

from __future__ import annotations

import argparse
import csv
import io
import statistics
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIGSHARE_ZIP = ROOT / "data" / "raw" / "figshare" / "CropProduction_JP_1883-2022.zip"
INNER_CSV = "CropProduction_JP_1883-2022/CropProduction_JP_1883-2022.csv"
BD_CSV = ROOT / "data" / "early_modern" / "rice_price_index.csv"
SCARCITY_CSV = ROOT / "data" / "early_modern" / "rice_yield_scarcity_index.csv"
CC_START = 1883
CC_END = 2022
MARKET = "edo"
YIELD_REF_YEARS = range(1883, 1893)
SOURCE_NOTE = (
  "figshare CC-BY 4.0 rice yield inverse (Buareal et al. "
  "10.6084/m9.figshare.29135699); scarcity not Osaka market quotes"
)


def nationalRiceYieldByYear(zipPath: Path) -> dict[int, float]:
  totals: dict[int, list[float]] = {}
  with zipfile.ZipFile(zipPath) as archive:
    with archive.open(INNER_CSV) as handle:
      reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig"))
      for row in reader:
        if row.get("crop") != "Rice" or row.get("var") != "yield":
          continue
        rawValue = str(row.get("value") or "").strip()
        if rawValue in ("", "NA", "nan"):
          continue
        try:
          year = int(row["year"])
          value = float(rawValue)
        except (KeyError, TypeError, ValueError):
          continue
        if value <= 0:
          continue
        totals.setdefault(year, []).append(value)
  return {year: statistics.mean(values) for year, values in totals.items() if values}


def yieldToRiceIndex(yieldByYear: dict[int, float]) -> dict[int, float]:
  refValues = [yieldByYear[year] for year in YIELD_REF_YEARS if year in yieldByYear]
  ref = statistics.mean(refValues) if refValues else statistics.mean(yieldByYear.values())
  return {year: ref / value for year, value in sorted(yieldByYear.items())}


def writeIndex(path: Path, rows: list[dict[str, str]]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["year", "market", "riceIndex", "evidence", "sourceNote"],
    )
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--fill-sim",
    action="store_true",
    help="Also rebuild inferred 1603-1882 archive (not BD, not loaded)",
  )
  args = parser.parse_args()
  if not FIGSHARE_ZIP.exists():
    raise SystemExit(f"Missing {FIGSHARE_ZIP}")
  yieldByYear = nationalRiceYieldByYear(FIGSHARE_ZIP)
  ccIndex = yieldToRiceIndex(yieldByYear)
  ccRows = [
    {
      "year": str(year),
      "market": MARKET,
      "riceIndex": f"{ccIndex[year]:.4f}",
      "evidence": "real_yield_inverse",
      "sourceNote": SOURCE_NOTE,
    }
    for year in range(CC_START, CC_END + 1)
    if year in ccIndex
  ]
  writeIndex(BD_CSV, ccRows)
  writeIndex(SCARCITY_CSV, ccRows)
  from src.historical_track import earlyModernRiceByYear

  earlyModernRiceByYear.cache_clear()
  print(f"BD rice years={len(ccRows)} {BD_CSV}")
  if args.fill_sim:
    print("--fill-sim is archived-only; run ingest_cc_rice_index.py legacy path if needed")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
