"""Fidelity catch-up and era-basket PPP (no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.historical_track import scoreHistoricalFidelity, getHistoricalTarget
from src.monthly_engine import runMonthlySimulation
from src.purchasing_power import computePurchasingPower, vibeLabel


def testRiceLogError() -> None:
  target = getHistoricalTarget(1783, 8)
  calm = scoreHistoricalFidelity(1.0, 1.08, 0.55, 1.20, target)
  extreme = scoreHistoricalFidelity(5.0, 1.08, 0.55, 1.20, target)
  assert extreme["riceErr"] < 1.5
  assert extreme["riceErr"] > calm["riceErr"]


def testEraPppStory() -> None:
  edo = computePurchasingPower(
    zundaPrice=1.0,
    ankoPrice=1.0,
    ricePrice=1.0,
    foodPerCapita=0.19,
    year=1603,
  )
  now = computePurchasingPower(
    zundaPrice=1.0,
    ankoPrice=1.0,
    ricePrice=1.0,
    foodPerCapita=0.12,
    year=2026,
    baselineFoodYen=edo.foodYenPerCapita,
  )
  assert edo.livingVsModern < 0.03
  assert edo.vibe in ("こんなしょぼい！！", "まだ貧しい")
  assert now.livingVsModern > 0.4
  assert now.developmentIndex > 2.5
  assert vibeLabel(now.livingVsModern, now.developmentIndex) != "こんなしょぼい！！"


def testHistoricalLegitimacyTracks() -> None:
  logPath = ROOT / "logs" / "test_fid_ppp_hist.jsonl"
  runMonthlySimulation(
    standard="edo_metal",
    start="1603-01",
    end="1612-12",
    useLlm=False,
    historicalPolicy=True,
    logPath=logPath,
    checkpointPath=ROOT / "logs" / "test_fid_ppp_hist.ckpt.json",
    anomalyPath=ROOT / "logs" / "test_fid_ppp_hist_anomaly.json",
  )
  rows = [json.loads(line) for line in logPath.read_text(encoding="utf-8").splitlines() if line.strip()]
  last = rows[-1]["historicalFidelity"]
  assert last["legitimacyErr"] < 0.15, last
  scores = [row["historicalFidelity"]["score"] for row in rows]
  assert sum(scores) / len(scores) >= 0.78


def main() -> int:
  testRiceLogError()
  testEraPppStory()
  testHistoricalLegitimacyTracks()
  print("test_fidelity_ppp: OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
