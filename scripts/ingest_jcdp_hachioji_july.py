"""Merge JCDP Hachioji July temperature anomaly into climate_monthly.csv.

Raw file (misnamed .zip on download): data/raw/jcdp/hachioji_july.zip
Format: year,Hachioji-Est.,Tokyo-Obs.

July anomaly -> climateIndex for months 6–8 (weighted). Existing Kyoto cherry
rows are kept; JCDP overwrites/blends summer months where available.

Cite: Mikami 1996; https://jcdp.jp/reconstructed-climate-indices/
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_RAW = WORKSPACE / "data" / "raw" / "jcdp" / "hachioji_july.zip"
DEFAULT_BASE = WORKSPACE / "data" / "processed" / "climate_monthly.csv"
DEFAULT_OUT = WORKSPACE / "data" / "processed" / "climate_monthly.csv"

TEMP_SCALE = 2.0  # degC per climateIndex unit
CLIMATE_CLIP = 1.2
# Month weights for applying July anomaly across summer.
SUMMER_WEIGHTS = {6: 0.45, 7: 1.0, 8: 0.55}


def parseHachiojiJuly(path: Path) -> dict[int, float]:
  text = path.read_text(encoding="utf-8-sig")
  byYear: dict[int, float] = {}
  for line in text.splitlines():
    if not line.strip() or line.lower().startswith("year") or line.startswith(","):
      # header like ",Hachioji-Est.,Tokyo-Obs."
      if "Hachioji" in line or "Tokyo" in line:
        continue
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2:
      continue
    try:
      year = int(parts[0])
    except ValueError:
      continue
    tempRaw = parts[1]
    if not tempRaw:
      continue
    try:
      byYear[year] = float(tempRaw)
    except ValueError:
      continue
  return byYear


def tempToIndex(tempC: float, meanC: float) -> float:
  value = (tempC - meanC) / TEMP_SCALE
  return max(min(value, CLIMATE_CLIP), -CLIMATE_CLIP)


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
  parser = argparse.ArgumentParser(description="Ingest JCDP Hachioji July temps")
  parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
  parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
  parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
  parser.add_argument("--start", type=int, default=1603)
  parser.add_argument("--end", type=int, default=2026)
  args = parser.parse_args()

  if not args.raw.exists():
    raise SystemExit(f"Missing raw: {args.raw}")

  temps = parseHachiojiJuly(args.raw)
  if not temps:
    raise SystemExit("No temperature rows parsed")
  meanC = statistics.mean(temps.values())
  existing = loadExisting(args.base)

  for year, tempC in temps.items():
    if year < args.start or year > args.end:
      continue
    annual = tempToIndex(tempC, meanC)
    for month, weight in SUMMER_WEIGHTS.items():
      key = f"{year:04d}-{month:02d}"
      climateIndex = annual * weight
      disaster = max(min(1.0 + min(climateIndex, 0.0), 1.0), 0.2)
      prev = existing.get(key)
      if prev is not None:
        try:
          prevIndex = float(prev.get("climateIndex", 0.0))
        except ValueError:
          prevIndex = 0.0
        # Prefer JCDP in summer: 70% JCDP + 30% prior (Kyoto).
        climateIndex = 0.3 * prevIndex + 0.7 * climateIndex
        disaster = max(min(1.0 + min(climateIndex, 0.0), 1.0), 0.2)
        source = "kyoto_cherry+jcdp_hachioji_july"
        notes = f"prev={prev.get('source')};julyC={tempC:.2f};mean={meanC:.2f};w={weight}"
      else:
        source = "jcdp_hachioji_july"
        notes = f"julyC={tempC:.2f};mean={meanC:.2f};w={weight}"
      existing[key] = {
        "yearMonth": key,
        "climateIndex": f"{climateIndex:.4f}",
        "disasterMultiplier": f"{disaster:.4f}",
        "source": source,
        "notes": notes,
      }

  args.out.parent.mkdir(parents=True, exist_ok=True)
  ordered = [existing[key] for key in sorted(existing.keys())]
  with args.out.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=["yearMonth", "climateIndex", "disasterMultiplier", "source", "notes"],
    )
    writer.writeheader()
    writer.writerows(ordered)
  print(f"merged {len(temps)} July years into {args.out} (total rows={len(ordered)}) meanC={meanC:.3f}")


if __name__ == "__main__":
  main()
