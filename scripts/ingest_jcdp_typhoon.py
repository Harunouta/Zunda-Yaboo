"""Apply JCDP Japan typhoon landfall months (1877-2020) as disaster dips.

Raw: data/raw/jcdp/typhoon_1877_2020.csv
https://jcdp.jp/wp-content/uploads/2021/01/TyphoonData1877-2020.csv

Cite: Kubota et al. 2021 Climatic Change 164:29; https://jcdp.jp/reconstructed-typhoon-data/
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_RAW = WORKSPACE / "data" / "raw" / "jcdp" / "typhoon_1877_2020.csv"
DEFAULT_BASE = WORKSPACE / "data" / "processed" / "climate_monthly.csv"
DIP_PER_LANDFALL = 0.07
MAX_STACK = 3
CLIMATE_CLIP = 1.2
MONTH_NAME = {
  "JAN": 1,
  "FEB": 2,
  "MAR": 3,
  "APR": 4,
  "MAY": 5,
  "JUN": 6,
  "JUL": 7,
  "AUG": 8,
  "SEP": 9,
  "OCT": 10,
  "NOV": 11,
  "DEC": 12,
}


def parseLandfallCounts(path: Path) -> Counter[str]:
  counts: Counter[str] = Counter()
  text = path.read_text(encoding="utf-8-sig", errors="replace")
  lines = text.splitlines()
  if len(lines) < 3:
    return counts
  for line in lines[2:]:
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 3:
      continue
    try:
      year = int(parts[0])
    except ValueError:
      continue
    monthToken = parts[1].upper()[:3]
    month = MONTH_NAME.get(monthToken)
    if month is None:
      try:
        month = int(parts[1])
      except ValueError:
        continue
    if month < 1 or month > 12:
      continue
    counts[f"{year:04d}-{month:02d}"] += 1
  return counts


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


def main() -> None:
  parser = argparse.ArgumentParser(description="Ingest JCDP typhoon landfall months")
  parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
  parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
  parser.add_argument("--out", type=Path, default=DEFAULT_BASE)
  args = parser.parse_args()
  if not args.raw.exists():
    raise SystemExit(f"Missing raw: {args.raw}")

  counts = parseLandfallCounts(args.raw)
  if not counts:
    raise SystemExit("No typhoon landfalls parsed")
  existing = loadExisting(args.base)
  applied = 0
  for key, nLandfall in counts.items():
    stack = min(int(nLandfall), MAX_STACK)
    dip = DIP_PER_LANDFALL * stack
    prev = existing.get(key)
    if prev is not None:
      try:
        climateIndex = float(prev.get("climateIndex", 0.0))
      except ValueError:
        climateIndex = 0.0
      try:
        disaster = float(prev.get("disasterMultiplier", 1.0))
      except ValueError:
        disaster = 1.0
      source = str(prev.get("source") or "") + "+jcdp_typhoon"
      notes = f"{prev.get('notes')};landfalls={nLandfall}"
    else:
      climateIndex = 0.0
      disaster = 1.0
      source = "jcdp_typhoon"
      notes = f"landfalls={nLandfall}"
    climateIndex = max(min(climateIndex - dip, CLIMATE_CLIP), -CLIMATE_CLIP)
    disaster = max(min(disaster - dip, 1.0), 0.2)
    existing[key] = {
      "yearMonth": key,
      "climateIndex": f"{climateIndex:.4f}",
      "disasterMultiplier": f"{disaster:.4f}",
      "source": source,
      "notes": notes,
    }
    applied += 1

  ordered = [existing[key] for key in sorted(existing.keys())]
  args.out.parent.mkdir(parents=True, exist_ok=True)
  with args.out.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(ordered)
  print(f"applied {applied} typhoon months ({sum(counts.values())} landfalls); rows={len(ordered)}")


if __name__ == "__main__":
  main()
