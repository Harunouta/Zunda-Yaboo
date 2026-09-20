#!/usr/bin/env python3
"""Run historical 1603→Nixon with dedicated log/checkpoint (v2 population 万人)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.monthly_engine import runMonthlySimulation

RUN_DIR = ROOT / "logs" / "runs" / "historical_1603_nixon_v2"
CKPT = ROOT / "checkpoints" / "v2_nixon" / "latest.json"
LOG = RUN_DIR / "monthly.jsonl"
ANOMALY = RUN_DIR / "anomaly_months.json"


def main() -> int:
  RUN_DIR.mkdir(parents=True, exist_ok=True)
  CKPT.parent.mkdir(parents=True, exist_ok=True)
  print(
    f"v2 nixon run start → log={LOG} ckpt={CKPT}",
    flush=True,
  )
  runMonthlySimulation(
    standard="edo_metal",
    start="1603-01",
    end="1971-08",
    useLlm=False,
    resume=False,
    historicalPolicy=True,
    logPath=LOG,
    checkpointPath=CKPT,
    anomalyPath=ANOMALY,
    seed=42,
    followRegimes=True,
  )
  print("v2 nixon run DONE", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
