"""Build data/processed/climate_monthly.csv from Kyoto cherry flowering DOY (NOAA paleo).

Late full-bloom DOY => colder spring proxy => negative climateIndex around Mar-May.
Other months get a damped annual echo so the series is continuous.

Cite: Aono & Saito / Aono & Kazui; NOAA study
https://www1.ncdc.noaa.gov/pub/data/paleo/historical/phenology/japan/kyoto2010flower.txt
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_RAW = WORKSPACE / "data" / "raw" / "noaa" / "kyoto2010flower.txt"
DEFAULT_OUT = WORKSPACE / "data" / "processed" / "climate_monthly.csv"

# Historical mean full-bloom DOY used as zero anomaly (approx. early April).
REFERENCE_DOY = 97.0
# climateIndex ~= -anomalyDays / scale (clipped).
DOY_SCALE = 20.0
CLIMATE_CLIP = 1.2
# Months that feel the spring phenology strongest.
SPRING_WEIGHTS = {
  1: 0.15,
  2: 0.35,
  3: 1.0,
  4: 1.0,
  5: 0.7,
  6: 0.25,
  7: 0.1,
  8: 0.05,
  9: 0.05,
  10: 0.1,
  11: 0.15,
  12: 0.15,
}


def parseKyotoFlowerFile(path: Path) -> dict[int, float]:
  """Return year -> full-bloom DOY for years with numeric DOY."""
  byYear: dict[int, float] = {}
  for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
    if not line.strip() or line.lstrip().startswith("#"):
      continue
    parts = line.split()
    if len(parts) < 2:
      continue
    try:
      year = int(parts[0])
      doy = float(parts[1])
    except ValueError:
      continue
    if doy <= 0:
      continue
    byYear[year] = doy
  return byYear


def doyToClimateIndex(doy: float, referenceDoy: float = REFERENCE_DOY) -> float:
  anomaly = doy - referenceDoy
  value = -anomaly / DOY_SCALE
  return max(min(value, CLIMATE_CLIP), -CLIMATE_CLIP)


def buildMonthlyRows(
  byYear: dict[int, float],
  startYear: int,
  endYear: int,
) -> list[dict[str, str]]:
  doys = list(byYear.values())
  ref = statistics.median(doys) if doys else REFERENCE_DOY
  rows: list[dict[str, str]] = []
  for year in range(startYear, endYear + 1):
    if year not in byYear:
      continue
    annual = doyToClimateIndex(byYear[year], referenceDoy=ref)
    for month in range(1, 13):
      weight = SPRING_WEIGHTS[month]
      climateIndex = annual * weight
      disaster = 1.0 + min(climateIndex, 0.0)
      rows.append({
        "yearMonth": f"{year:04d}-{month:02d}",
        "climateIndex": f"{climateIndex:.4f}",
        "disasterMultiplier": f"{max(min(disaster, 1.0), 0.2):.4f}",
        "source": "kyoto_cherry_doy",
        "notes": f"doy={byYear[year]:.0f};ref={ref:.1f};w={weight}",
      })
  return rows


def main() -> None:
  parser = argparse.ArgumentParser(description="Ingest Kyoto cherry DOY into climate_monthly.csv")
  parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
  parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
  parser.add_argument("--start", type=int, default=1603)
  parser.add_argument("--end", type=int, default=2010)
  args = parser.parse_args()

  if not args.raw.exists():
    raise SystemExit(f"Missing raw file: {args.raw}")

  byYear = parseKyotoFlowerFile(args.raw)
  rows = buildMonthlyRows(byYear, args.start, args.end)
  args.out.parent.mkdir(parents=True, exist_ok=True)
  with args.out.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(rows)
  print(f"wrote {len(rows)} rows to {args.out} from {len(byYear)} annual DOY points")


if __name__ == "__main__":
  main()
