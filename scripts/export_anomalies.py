"""Re-export anomaly months from an existing monthly JSONL log."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.monthly_engine import exportAnomalies  # noqa: E402


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--log", required=True, help="Path to monthly JSONL")
  parser.add_argument("--out", required=True, help="Output anomaly JSON path")
  args = parser.parse_args()
  logPath = Path(args.log)
  outPath = Path(args.out)
  count = exportAnomalies(logPath, outPath)
  print(f"anomalies={count} log={logPath} out={outPath}")


if __name__ == "__main__":
  main()
