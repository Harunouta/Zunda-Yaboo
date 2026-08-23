"""LLM smoke: 2 months with zundamon mascot speech."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("LM_STUDIO_HOST", "localhost")

from src.monthly_engine import runMonthlySimulation

logPath = ROOT / "logs" / "llm_smoke_mascot.jsonl"
checkpointPath = ROOT / "checkpoints" / "llm_smoke.json"
anomalyPath = ROOT / "logs" / "llm_smoke_anomaly.json"

runMonthlySimulation(
  standard="zunda",
  start="1853-07",
  end="1853-08",
  useLlm=True,
  resume=False,
  logPath=logPath,
  checkpointPath=checkpointPath,
  anomalyPath=anomalyPath,
)

rows = [json.loads(line) for line in logPath.read_text(encoding="utf-8").splitlines() if line.strip()]
for row in rows:
  crowd = row["crowd"]
  print("---", row["yearMonth"], crowd.get("source"))
  print("mascotId:", crowd.get("mascotId"))
  print("mascotSpeech:", crowd.get("mascotSpeech"))
  print("decision:", row["llm"]["decisionSource"])
