"""Rice BD: Figshare years load; sim fill does not."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.historical_track import blendRiceIndex, earlyModernRiceByYear, getHistoricalTarget


def main() -> int:
  series = earlyModernRiceByYear()
  assert 1603 not in series
  assert 1882 not in series
  assert 1883 in series
  assert 2022 in series
  assert 2026 not in series
  tenmei = getHistoricalTarget(1783, 8)
  assert abs(tenmei.riceIndex - 1.80) < 0.01
  modern = blendRiceIndex(1993, 1.30)
  assert modern != 1.30
  print("test_rice_bd: OK", f"n={len(series)} 1883={series[1883]:.4f} 1993blend={modern:.4f}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
