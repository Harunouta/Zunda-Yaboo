"""Summarize metric distributions used by anomaly export (no LM Studio)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.monthly_engine import (  # noqa: E402
  CURRENCY_ABS_FLOOR,
  CURRENCY_REL_DROP_THRESHOLD,
  FIDELITY_DROP_THRESHOLD,
  FOOD_DROP_THRESHOLD,
  POPULATION_DROP_THRESHOLD,
  RIOT_RISK_THRESHOLD,
  collectAnomalyReasons,
  collectPriceShockThreshold,
  exportAnomalies,
  percentileSorted,
)


def loadRows(logPath: Path) -> list[dict]:
  return [
    json.loads(line)
    for line in logPath.read_text(encoding="utf-8").splitlines()
    if line.strip()
  ]


def summarizeSeries(name: str, values: list[float]) -> None:
  if not values:
    print(f"  {name}: (empty)")
    return
  ordered = sorted(values)
  print(
    f"  {name}: n={len(ordered)} min={ordered[0]:.4f} "
    f"p05={percentileSorted(ordered, 0.05):.4f} "
    f"p50={percentileSorted(ordered, 0.50):.4f} "
    f"p95={percentileSorted(ordered, 0.95):.4f} "
    f"p99={percentileSorted(ordered, 0.99):.4f} "
    f"max={ordered[-1]:.4f}"
  )


def analyzeLog(logPath: Path) -> None:
  rows = loadRows(logPath)
  print(f"=== {logPath} months={len(rows)}")
  notes: list[float] = []
  riot: list[float] = []
  popDrop: list[float] = []
  foodDrop: list[float] = []
  notesRel: list[float] = []
  for index in range(1, len(rows)):
    prev = rows[index - 1]
    curr = rows[index]
    prevMacro = prev.get("macro") or {}
    currMacro = curr.get("macro") or {}
    notes.append(float(currMacro.get("notesValueRatio", 1.0)))
    riot.append(float((curr.get("crowd") or {}).get("riotRisk", 0.0) or 0.0))
    popDrop.append(float(prevMacro.get("population", 0.0)) - float(currMacro.get("population", 0.0)))
    foodDrop.append(float(prevMacro.get("foodBuffer", 0.0)) - float(currMacro.get("foodBuffer", 0.0)))
    prevNotes = float(prevMacro.get("notesValueRatio", 1.0))
    currNotes = float(currMacro.get("notesValueRatio", 1.0))
    notesRel.append((prevNotes - currNotes) / max(prevNotes, 1e-9))

  summarizeSeries("notesValueRatio", notes)
  summarizeSeries("riotRisk", riot)
  summarizeSeries("popDrop", popDrop)
  summarizeSeries("foodDrop", foodDrop)
  summarizeSeries("notesRelDrop", notesRel)

  priceShockThreshold = collectPriceShockThreshold(rows)
  reasonCounter: Counter[str] = Counter()
  anomalyCount = 0
  examples: list[tuple[str, list[str]]] = []
  for index in range(1, len(rows)):
    reasons = collectAnomalyReasons(rows[index - 1], rows[index], priceShockThreshold)
    if not reasons:
      continue
    anomalyCount += 1
    reasonCounter.update(reasons)
    if len(examples) < 12:
      examples.append((rows[index]["yearMonth"], reasons))

  monthPairs = max(len(rows) - 1, 1)
  print(
    f"  v2_preview count={anomalyCount}/{monthPairs} "
    f"({100.0 * anomalyCount / monthPairs:.2f}%) "
    f"priceShockThreshold={priceShockThreshold:.4f}"
  )
  print(f"  thresholds pop>{POPULATION_DROP_THRESHOLD} food>{FOOD_DROP_THRESHOLD} "
        f"riot>={RIOT_RISK_THRESHOLD} nvrAbs<{CURRENCY_ABS_FLOOR} "
        f"nvrRel>={CURRENCY_REL_DROP_THRESHOLD} fidelityDrop>={FIDELITY_DROP_THRESHOLD}")
  print(f"  reasons={reasonCounter.most_common(20)}")
  print(f"  examples={examples}")


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--log", action="append", required=True, help="JSONL run path (repeatable)")
  parser.add_argument("--export", action="store_true", help="Also write anomaly JSON beside each log")
  parser.add_argument(
    "--suffix",
    default="_anomaly_v2.json",
    help="Suffix replacing .jsonl when --export (default: _anomaly_v2.json)",
  )
  args = parser.parse_args()
  for logArg in args.log:
    logPath = Path(logArg)
    analyzeLog(logPath)
    if args.export:
      outPath = logPath.with_name(logPath.name.replace(".jsonl", args.suffix))
      if not str(outPath).endswith(".json"):
        outPath = Path(str(logPath) + args.suffix)
      count = exportAnomalies(logPath, outPath)
      print(f"  wrote {outPath} count={count}")


if __name__ == "__main__":
  main()
