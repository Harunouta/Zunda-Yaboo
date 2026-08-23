"""Merge Lake Suwa freeze / Omiwatari winter proxy into climate_monthly.csv.

Place a CSV at data/raw/suwa/omiwatari.csv (gitignored) with columns:
  year,freezeDoy,omiwatari
- freezeDoy: day-of-year of complete freeze (or blank if none)
- omiwatari: 1 if Omiwatari reported, 0 if not, blank if unknown

Early freeze → cold winter (negative climateIndex for Dec–Feb).
No freeze / late freeze → mild winter (positive climateIndex).

Public dump used here: NSIDC G01377 (Lake Suwa code ARAI1). Unrestricted NOAA@NSIDC.
EDI knb-lter-ntl.327 is CC BY 4.0 but PASTA often 403 from this host — keep as preferred cite if you can download.

Cite: NSIDC G01377; Sharma et al. Sci Rep 2016 (CC BY paper); JCDP omiwatari page.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import statistics
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_RAW = WORKSPACE / "data" / "raw" / "suwa" / "omiwatari.csv"
DEFAULT_SAMPLE = WORKSPACE / "data" / "redistributable" / "suwa_omiwatari_sample.csv"
DEFAULT_NSIDC = WORKSPACE / "data" / "raw" / "suwa" / "liag_freeze_thaw_table.csv"
SUWA_LAKECODE = "ARAI1"
MISSING_INT = -999
DEFAULT_BASE = WORKSPACE / "data" / "processed" / "climate_monthly.csv"
DEFAULT_OUT = DEFAULT_BASE

CLIMATE_CLIP = 1.2
WINTER_WEIGHTS = {12: 0.7, 1: 1.0, 2: 0.85}
# Reference: mid-January freeze ≈ DOY 15 (calendar year of Jan/Feb winter end).
REF_FREEZE_DOY = 15.0
DOY_SCALE = 25.0


def winterCenteredDoy(year: int, month: int, day: int) -> float:
  """Jan 1 = 0; December freeze is negative (early = cold)."""
  stamp = datetime.date(year, month, day)
  doy = stamp.timetuple().tm_yday
  if month >= 8:
    daysInYear = 366 if datetime.date(year, 12, 31).timetuple().tm_yday == 366 else 365
    return float(doy - daysInYear)
  return float(doy)


def extractNsIdcSuwa(nsidcPath: Path, outPath: Path) -> int:
  """Write year,freezeDoy,omiwatari from NSIDC G01377 Lake Suwa rows."""
  winters: dict[int, dict[str, str]] = {}
  with nsidcPath.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    for raw in reader:
      if str(raw.get("lakecode") or "").strip().upper() != SUWA_LAKECODE:
        continue
      froze = str(raw.get("froze") or "").strip().upper()
      try:
        iceYear = int(raw.get("iceon_year") or MISSING_INT)
        iceMonth = int(raw.get("iceon_month") or MISSING_INT)
        iceDay = int(raw.get("iceon_day") or MISSING_INT)
      except ValueError:
        continue
      year = iceYear if iceYear != MISSING_INT else None
      if year is None:
        season = str(raw.get("season") or "")
        if "-" in season:
          try:
            year = int(season.split("-")[0]) + 1
          except ValueError:
            continue
        else:
          continue
      freezeDoy = ""
      if froze == "Y" and iceMonth != MISSING_INT and iceDay != MISSING_INT and iceYear != MISSING_INT:
        freezeDoy = f"{winterCenteredDoy(iceYear, iceMonth, iceDay):.1f}"
      omiwatari = "0" if froze == "N" else ""
      winters[year] = {
        "year": str(year),
        "freezeDoy": freezeDoy,
        "omiwatari": omiwatari,
      }
  outPath.parent.mkdir(parents=True, exist_ok=True)
  with outPath.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["year", "freezeDoy", "omiwatari"])
    writer.writeheader()
    for year in sorted(winters):
      writer.writerow(winters[year])
  return len(winters)


def parseOmiwatariCsv(path: Path) -> dict[int, dict[str, float | None]]:
  rows: dict[int, dict[str, float | None]] = {}
  with path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    for raw in reader:
      try:
        year = int(str(raw.get("year") or "").strip())
      except ValueError:
        continue
      freezeRaw = str(raw.get("freezeDoy") or "").strip()
      omiRaw = str(raw.get("omiwatari") or "").strip()
      freezeDoy: float | None
      try:
        freezeDoy = float(freezeRaw) if freezeRaw else None
      except ValueError:
        freezeDoy = None
      omiwatari: float | None
      try:
        omiwatari = float(omiRaw) if omiRaw else None
      except ValueError:
        omiwatari = None
      rows[year] = {"freezeDoy": freezeDoy, "omiwatari": omiwatari}
  return rows


def winterIndex(freezeDoy: float | None, omiwatari: float | None) -> float:
  """Positive = warm winter, negative = cold (matches other climate ingest)."""
  if freezeDoy is None:
    # No freeze recorded → treat as warm.
    value = 0.85
  else:
    value = (freezeDoy - REF_FREEZE_DOY) / DOY_SCALE
  if omiwatari == 1.0:
    value -= 0.15
  elif omiwatari == 0.0 and freezeDoy is None:
    value += 0.1
  return max(min(value, CLIMATE_CLIP), -CLIMATE_CLIP)


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
  parser.add_argument("--sample", action="store_true", help="Use redistributable sample CSV")
  parser.add_argument("--from-nsidc", action="store_true", help="Extract Lake Suwa from NSIDC G01377 table")
  parser.add_argument("--nsidc", type=Path, default=DEFAULT_NSIDC)
  parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
  parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
  args = parser.parse_args()

  if args.from_nsidc:
    if not args.nsidc.exists():
      raise SystemExit(f"Missing NSIDC table: {args.nsidc}")
    written = extractNsIdcSuwa(args.nsidc, args.raw)
    print(f"extracted {written} Suwa winters -> {args.raw}")
    sourcePath = args.raw
  else:
    sourcePath = DEFAULT_SAMPLE if args.sample or not args.raw.exists() else args.raw
  if not sourcePath.exists():
    raise SystemExit(
      f"Missing Suwa CSV: {args.raw} (or pass --sample). "
      "See scripts/ingest_suwa_omiwatari.py docstring."
    )

  winters = parseOmiwatariCsv(sourcePath)
  if not winters:
    raise SystemExit(f"No rows parsed from {sourcePath}")

  existing: dict[str, dict[str, str]] = {}
  if args.base.exists():
    with args.base.open(encoding="utf-8", newline="") as handle:
      for raw in csv.DictReader(handle):
        existing[raw["yearMonth"]] = dict(raw)

  indices = [winterIndex(row["freezeDoy"], row["omiwatari"]) for row in winters.values()]
  meanIndex = statistics.mean(indices) if indices else 0.0

  for year, row in winters.items():
    annual = winterIndex(row["freezeDoy"], row["omiwatari"]) - meanIndex * 0.1
    annual = max(min(annual, CLIMATE_CLIP), -CLIMATE_CLIP)
    for month, weight in WINTER_WEIGHTS.items():
      # DJF labeled by winter-end year: Dec uses previous calendar year.
      calYear = year - 1 if month == 12 else year
      key = f"{calYear:04d}-{month:02d}"
      climateIndex = annual * weight
      prev = existing.get(key)
      if prev is not None:
        prevIndex = float(prev.get("climateIndex", 0.0) or 0.0)
        climateIndex = 0.4 * prevIndex + 0.6 * climateIndex
        source = f"{prev.get('source', 'prior')}+suwa_omiwatari"
      else:
        source = "suwa_omiwatari"
      disaster = max(min(1.0 + min(climateIndex, 0.0), 1.0), 0.2)
      existing[key] = {
        "yearMonth": key,
        "climateIndex": f"{climateIndex:.4f}",
        "disasterMultiplier": f"{disaster:.4f}",
        "source": source,
        "notes": (
          f"freezeDoy={row['freezeDoy']};omiwatari={row['omiwatari']};"
          f"file={sourcePath.name};w={weight}"
        ),
      }

  ordered = [existing[key] for key in sorted(existing.keys())]
  args.out.parent.mkdir(parents=True, exist_ok=True)
  with args.out.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(ordered)
  print(
    f"merged {len(winters)} Suwa winters from {sourcePath.name}; "
    f"rows={len(ordered)} meanProxy={meanIndex:.3f}"
  )


if __name__ == "__main__":
  main()
