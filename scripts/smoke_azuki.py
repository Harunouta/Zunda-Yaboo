"""Smoke the dried-azuki standard (independent of anko paste)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mascot import mascotForStandard  # noqa: E402
from src.monthly_engine import runMonthlySimulation  # noqa: E402

LOG = ROOT / "logs" / "runs" / "smoke_azuki_1603_1604.jsonl"


def main() -> int:
  assert mascotForStandard("azuki") == "ankomon"
  runMonthlySimulation(
    standard="azuki",
    start="1603-01",
    end="1604-12",
    useLlm=False,
    resume=False,
    historicalPolicy=False,
    logPath=LOG,
    checkpointPath=ROOT / "logs" / "smoke_azuki_1603_1604.ckpt.json",
    anomalyPath=ROOT / "logs" / "smoke_azuki_1603_1604_anomaly.json",
    opinionLeaderCount=0,
    opinionParallel=False,
  )
  rows = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
  assert len(rows) == 24
  first = rows[0]
  last = rows[-1]
  assert first.get("monetaryStandard") == "azuki"
  macroFirst = first.get("macro") or {}
  crowd = first.get("crowd") or {}
  assert float(macroFirst.get("azukiNotes") or 0) > 0
  assert float(macroFirst.get("azukiStock") or 0) > 0
  assert crowd.get("mascotId") == "ankomon"
  assert (first.get("prices") or {}).get("azukiPrice", 0) > 0
  assert (last.get("macro") or {}).get("population", 0) > 500
  print(
    f"ok azuki {first.get('yearMonth')}..{last.get('yearMonth')} "
    f"pop={last.get('macro', {}).get('population')} "
    f"azukiNotes={last.get('macro', {}).get('azukiNotes')} "
    f"mascot={crowd.get('mascotId')}"
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
