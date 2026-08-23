"""Merge Kawanishi DJF winter temperature anomaly into climate_monthly.csv.

Raw: data/raw/jcdp/kawanishi_djf.csv
Cite: Hirano et al. 2012; https://jcdp.jp/reconstructed-climate-indices/
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_RAW = WORKSPACE / "data" / "raw" / "jcdp" / "kawanishi_djf.csv"
DEFAULT_BASE = WORKSPACE / "data" / "processed" / "climate_monthly.csv"
DEFAULT_OUT = DEFAULT_BASE

TEMP_SCALE = 2.0
CLIMATE_CLIP = 1.2
# DJF mean applied across Dec–Feb of the winter ending in `year` (DJF of year).
WINTER_MONTHS = {
  # month -> (yearOffset, weight); yearOffset 0 = same calendar year as DJF label year
  12: (-1, 0.7),  # Dec of previous calendar year
  1: (0, 1.0),
  2: (0, 0.85),
}


def parseKawanishiDjf(path: Path) -> dict[int, float]:
  byYear: dict[int, float] = {}
  text = path.read_text(encoding="utf-8-sig")
  for line in text.splitlines():
    if not line.strip() or line.lower().startswith("year"):
      continue
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2 or not parts[1]:
      continue
    try:
      byYear[int(parts[0])] = float(parts[1])
    except ValueError:
      continue
  return byYear


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
  parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
  parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
  args = parser.parse_args()
  temps = parseKawanishiDjf(args.raw)
  meanC = statistics.mean(temps.values())
  existing: dict[str, dict[str, str]] = {}
  if args.base.exists():
    with args.base.open(encoding="utf-8", newline="") as handle:
      for raw in csv.DictReader(handle):
        existing[raw["yearMonth"]] = dict(raw)

  for year, tempC in temps.items():
    annual = max(min((tempC - meanC) / TEMP_SCALE, CLIMATE_CLIP), -CLIMATE_CLIP)
    for month, (yearOffset, weight) in WINTER_MONTHS.items():
      calYear = year + yearOffset
      key = f"{calYear:04d}-{month:02d}"
      climateIndex = annual * weight
      prev = existing.get(key)
      if prev is not None:
        prevIndex = float(prev.get("climateIndex", 0.0) or 0.0)
        climateIndex = 0.3 * prevIndex + 0.7 * climateIndex
        source = f"{prev.get('source', 'prior')}+jcdp_kawanishi_djf"
      else:
        source = "jcdp_kawanishi_djf"
      disaster = max(min(1.0 + min(climateIndex, 0.0), 1.0), 0.2)
      existing[key] = {
        "yearMonth": key,
        "climateIndex": f"{climateIndex:.4f}",
        "disasterMultiplier": f"{disaster:.4f}",
        "source": source,
        "notes": f"djfC={tempC:.2f};mean={meanC:.2f};w={weight}",
      }

  ordered = [existing[key] for key in sorted(existing.keys())]
  with args.out.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(ordered)
  print(f"merged {len(temps)} DJF years; rows={len(ordered)} meanC={meanC:.3f}")


if __name__ == "__main__":
  main()
