"""Merge Zaiki et al. West Japan Temperature (WJT) monthly anomalies into climate_monthly.csv.

Raw CSV: data/raw/jcdp/wjt1821_2000.csv (from JCDP download 1062 .xls).
Anomalies are degC vs 1971-2000. Missing = -9999.

Cite: Zaiki et al. 2006 Int. J. Climatol. 26:399-423; https://jcdp.jp/instrumental-meteorological-data/
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_RAW = WORKSPACE / "data" / "raw" / "jcdp" / "wjt1821_2000.csv"
DEFAULT_BASE = WORKSPACE / "data" / "processed" / "climate_monthly.csv"
MISSING = -9999.0
TEMP_SCALE = 2.0
CLIMATE_CLIP = 1.2
BLEND_WJT = 0.6
MONTH_COLS = (
  "JAN",
  "FEB",
  "MAR",
  "APR",
  "MAY",
  "JUN",
  "JUL",
  "AUG",
  "SEP",
  "OCT",
  "NOV",
  "DEC",
)


def parseWjtCsv(path: Path) -> dict[tuple[int, int], float]:
  byMonth: dict[tuple[int, int], float] = {}
  with path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    for raw in reader:
      try:
        year = int(float(str(raw.get("WJT") or "").strip()))
      except ValueError:
        continue
      for month, col in enumerate(MONTH_COLS, start=1):
        try:
          value = float(raw.get(col) or MISSING)
        except (TypeError, ValueError):
          continue
        if value <= MISSING + 1:
          continue
        byMonth[(year, month)] = value
  return byMonth


def loadExisting(path: Path) -> dict[str, dict[str, str]]:
  if not path.exists():
    return {}
  rows: dict[str, dict[str, str]] = {}
  with path.open(encoding="utf-8", newline="") as handle:
    for raw in csv.DictReader(handle):
      key = str(raw.get("yearMonth") or "")
      if key:
        rows[key] = dict(raw)
  return rows


def writeClimate(path: Path, rows: dict[str, dict[str, str]]) -> None:
  ordered = [rows[key] for key in sorted(rows.keys())]
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(ordered)


def main() -> None:
  parser = argparse.ArgumentParser(description="Ingest JCDP WJT monthly temperature anomalies")
  parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
  parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
  parser.add_argument("--out", type=Path, default=DEFAULT_BASE)
  args = parser.parse_args()
  if not args.raw.exists():
    raise SystemExit(f"Missing raw: {args.raw}")

  series = parseWjtCsv(args.raw)
  if not series:
    raise SystemExit("No WJT months parsed")
  existing = loadExisting(args.base)
  merged = 0
  for (year, month), anomalyC in series.items():
    key = f"{year:04d}-{month:02d}"
    wjtIndex = max(min(anomalyC / TEMP_SCALE, CLIMATE_CLIP), -CLIMATE_CLIP)
    prev = existing.get(key)
    if prev is not None:
      try:
        prevIndex = float(prev.get("climateIndex", 0.0))
      except ValueError:
        prevIndex = 0.0
      climateIndex = (1.0 - BLEND_WJT) * prevIndex + BLEND_WJT * wjtIndex
      source = str(prev.get("source") or "") + "+jcdp_wjt"
      notes = f"{prev.get('notes')};wjtC={anomalyC:.2f}"
    else:
      climateIndex = wjtIndex
      source = "jcdp_wjt"
      notes = f"wjtC={anomalyC:.2f}"
    disaster = max(min(1.0 + min(climateIndex, 0.0), 1.0), 0.2)
    existing[key] = {
      "yearMonth": key,
      "climateIndex": f"{climateIndex:.4f}",
      "disasterMultiplier": f"{disaster:.4f}",
      "source": source,
      "notes": notes,
    }
    merged += 1
  writeClimate(args.out, existing)
  print(f"merged {merged} WJT months into {args.out} (rows={len(existing)})")


if __name__ == "__main__":
  main()
