"""Smoke: mediators persist/decay and historical policies auto-fire."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.events import getEventPayload, reloadEventData  # noqa: E402
from src.monthly_engine import runMonthlySimulation  # noqa: E402
from src.policies import historicalPoliciesForMonth  # noqa: E402

LOG = ROOT / "logs" / "runs" / "smoke_mediators_hoei.jsonl"


def main() -> int:
  reloadEventData()
  hoe = getEventPayload("hoei_fuji_eruption_2")
  assert hoe is not None
  assert hoe.landPollution > 0.0
  assert hoe.infraDamage > 0.0
  assert any(item.policyId == "sankin_kotai" for item in historicalPoliciesForMonth("1635-06"))

  runMonthlySimulation(
    standard="edo_metal",
    start="1707-09",
    end="1708-02",
    useLlm=False,
    resume=False,
    historicalPolicy=True,
    logPath=LOG,
    opinionLeaderCount=0,
    opinionParallel=False,
  )
  rows = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
  byMonth = {row["yearMonth"]: row for row in rows}
  quiet = byMonth["1707-09"]["mediators"]["areas"]["edo_core"]["landPollution"]
  peak = byMonth["1707-12"]["mediators"]["areas"]["edo_core"]["landPollution"]
  later = byMonth["1708-02"]["mediators"]["areas"]["edo_core"]["landPollution"]
  assert peak > quiet, f"land pollution should rise ({quiet} -> {peak})"
  assert later < peak, f"land pollution should decay ({peak} -> {later})"
  assert byMonth["1707-12"]["prices"]["ricePrice"] > byMonth["1707-09"]["prices"]["ricePrice"]
  print("smoke_mediators_policies: OK", "peak", peak, "later", later)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
