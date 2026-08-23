"""Validity baselines:
1) First ~10 years zunda / anko stay stable and emit prices.
2) edo_metal + historical policy tracks Japanese history anchors.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.monthly_engine import runMonthlySimulation

LOG_DIR = ROOT / "logs"
MIN_POP_RATIO = 0.85
MIN_AVG_FIDELITY = 0.55


def _loadRows(path: Path) -> list[dict]:
  return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _checkFirstDecade(standard: str) -> dict:
  logPath = LOG_DIR / f"baseline_{standard}_10y.jsonl"
  runMonthlySimulation(
    standard=standard,
    start="1603-01",
    end="1612-12",
    useLlm=False,
    historicalPolicy=False,
    logPath=logPath,
    checkpointPath=LOG_DIR / f"baseline_{standard}_10y.ckpt.json",
    anomalyPath=LOG_DIR / f"baseline_{standard}_10y_anomaly.json",
  )
  rows = _loadRows(logPath)
  firstPop = rows[0]["macro"]["population"]
  lastPop = rows[-1]["macro"]["population"]
  mascotByStandard = {"zunda": "zundamon", "anko": "ankomon", "azuki": "ankomon"}
  expectedMascot = mascotByStandard.get(standard)
  pricesOk = all(
    "prices" in row
    and row["prices"]["zundaPrice"] > 0
    and row["prices"]["ankoPrice"] > 0
    and (standard != "azuki" or float(row["prices"].get("azukiPrice") or 0) > 0)
    for row in rows
  )
  mascotOk = expectedMascot is not None and all(
    row.get("crowd", {}).get("mascotId") == expectedMascot for row in rows
  )
  popOk = lastPop >= firstPop * MIN_POP_RATIO
  return {
    "standard": standard,
    "months": len(rows),
    "firstPop": firstPop,
    "lastPop": lastPop,
    "popOk": popOk,
    "pricesOk": pricesOk,
    "mascotOk": mascotOk,
    "samplePrices": rows[-1]["prices"],
    "ok": popOk and pricesOk and mascotOk and len(rows) == 120,
  }


def _checkHistoricalEdo() -> dict:
  logPath = LOG_DIR / "baseline_edo_metal_hist.jsonl"
  # Sparse but includes founding + tenmei + perry window for fidelity score.
  runMonthlySimulation(
    standard="edo_metal",
    start="1603-01",
    end="1612-12",
    useLlm=False,
    historicalPolicy=True,
    logPath=logPath,
    checkpointPath=LOG_DIR / "baseline_edo_metal_hist.ckpt.json",
    anomalyPath=LOG_DIR / "baseline_edo_metal_hist_anomaly.json",
  )
  rows = _loadRows(logPath)
  scores = [row["historicalFidelity"]["score"] for row in rows]
  avgScore = sum(scores) / max(len(scores), 1)
  pricesOk = all(row["prices"]["zundaPrice"] > 0 and row["prices"]["ankoPrice"] > 0 for row in rows)
  return {
    "standard": "edo_metal",
    "months": len(rows),
    "avgFidelity": round(avgScore, 4),
    "minFidelity": round(min(scores), 4) if scores else 0.0,
    "pricesOk": pricesOk,
    "samplePrices": rows[-1]["prices"],
    "sampleFidelity": rows[-1]["historicalFidelity"],
    "ok": avgScore >= MIN_AVG_FIDELITY and pricesOk and len(rows) == 120,
  }


def runBaselines() -> int:
  LOG_DIR.mkdir(parents=True, exist_ok=True)
  reports = [
    _checkFirstDecade("zunda"),
    _checkFirstDecade("anko"),
    _checkFirstDecade("azuki"),
    _checkHistoricalEdo(),
  ]
  outPath = LOG_DIR / "validity_baseline_report.json"
  outPath.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
  print(json.dumps(reports, ensure_ascii=False, indent=2))
  allOk = all(item["ok"] for item in reports)
  print(f"validity_baseline={'PASS' if allOk else 'FAIL'} report={outPath}")
  return 0 if allOk else 1


if __name__ == "__main__":
  raise SystemExit(runBaselines())
