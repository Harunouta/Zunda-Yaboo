"""Fill missing yearMonth rows by copying the nearest same-calendar-month observation."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_CSV = WORKSPACE / "data" / "processed" / "climate_monthly.csv"
SEARCH_YEARS = 80


def loadExisting(path: Path) -> dict[str, dict[str, str]]:
  rows: dict[str, dict[str, str]] = {}
  with path.open(encoding="utf-8", newline="") as handle:
    for raw in csv.DictReader(handle):
      key = str(raw.get("yearMonth") or "")
      if key:
        rows[key] = dict(raw)
  return rows


def nearestSameMonth(
  existing: dict[str, dict[str, str]],
  year: int,
  month: int,
) -> dict[str, str] | None:
  for delta in range(1, SEARCH_YEARS + 1):
    for candYear in (year - delta, year + delta):
      key = f"{candYear:04d}-{month:02d}"
      if key in existing and "gapfill" not in str(existing[key].get("source") or ""):
        return existing[key]
    for candYear in (year - delta, year + delta):
      key = f"{candYear:04d}-{month:02d}"
      if key in existing:
        return existing[key]
  return None


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
  parser.add_argument("--start", type=int, default=1603)
  parser.add_argument("--end-year", dest="endYear", type=int, default=2026)
  parser.add_argument("--end-month", dest="endMonth", type=int, default=8)
  args = parser.parse_args()
  existing = loadExisting(args.csv)
  filled = 0
  year = args.start
  month = 1
  while (year, month) <= (args.endYear, args.endMonth):
    key = f"{year:04d}-{month:02d}"
    if key not in existing:
      donor = nearestSameMonth(existing, year, month)
      if donor is not None:
        existing[key] = {
          "yearMonth": key,
          "climateIndex": donor.get("climateIndex", "0"),
          "disasterMultiplier": donor.get("disasterMultiplier", "1"),
          "source": str(donor.get("source") or "unknown") + "+gapfill",
          "notes": f"from={donor.get('yearMonth')}",
        }
        filled += 1
    month += 1
    if month > 12:
      month = 1
      year += 1

  ordered = [existing[key] for key in sorted(existing.keys())]
  with args.csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(ordered)
  print(f"gapfill added {filled} months; rows={len(ordered)}")


if __name__ == "__main__":
  main()
