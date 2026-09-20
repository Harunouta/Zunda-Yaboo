#!/usr/bin/env python3
"""Historical run 1970-01 → 2026-08 with yen FX regimes + population tune."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.monthly_engine import runMonthlySimulation

RUN_DIR = ROOT / "logs" / "runs" / "historical_1970_2026_v2"
CKPT = ROOT / "checkpoints" / "v2_1970_present" / "latest.json"
LOG = RUN_DIR / "monthly.jsonl"
ANOMALY = RUN_DIR / "anomaly_months.json"


def main() -> int:
  RUN_DIR.mkdir(parents=True, exist_ok=True)
  CKPT.parent.mkdir(parents=True, exist_ok=True)
  print(f"v2 1970→2026 start → log={LOG}", flush=True)
  runMonthlySimulation(
    standard="edo_metal",
    start="1970-01",
    end="2026-08",
    useLlm=False,
    resume=False,
    historicalPolicy=True,
    logPath=LOG,
    checkpointPath=CKPT,
    anomalyPath=ANOMALY,
    seed=42,
    followRegimes=True,
  )
  print("v2 1970→2026 DONE", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
