"""Rebuild data/processed/climate_monthly.csv from local raw files (gitignored)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
  ["ingest_kyoto_cherry.py"],
  ["ingest_jcdp_hachioji_july.py"],
  ["ingest_jcdp_kawanishi_july.py"],
  ["ingest_jcdp_kawanishi_djf.py"],
  ["ingest_suwa_omiwatari.py", "--from-nsidc"],
  ["ingest_jcdp_wjt.py"],
  ["ingest_jcdp_typhoon.py"],
  ["ingest_climate_gapfill.py"],
]


def main() -> int:
  for step in STEPS:
    script = ROOT / "scripts" / step[0]
    cmd = [sys.executable, str(script), *step[1:]]
    print(">>", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
      print(f"FAILED {step[0]}", flush=True)
      return result.returncode
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
