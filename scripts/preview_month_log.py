"""Pretty-print recent month behavior / mascot lines from a JSONL run log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_TAIL = 12


def loadRows(path: Path) -> list[dict]:
  rows: list[dict] = []
  for line in path.read_text(encoding="utf-8").splitlines():
    if line.strip():
      rows.append(json.loads(line))
  return rows


def formatRow(row: dict) -> str:
  yearMonth = row.get("yearMonth", "?")
  events = row.get("events") or []
  crowd = row.get("crowd") or {}
  behavior = row.get("behavior") or {}
  law = row.get("law") or {}
  opinion = row.get("opinionLeaders") or {}
  speech = behavior.get("mascotSpeech") or crowd.get("mascotSpeech") or ""
  lines = [
    f"## {yearMonth}  events={events or '-'}",
    f"  decree : {law.get('decree', '')}",
    f"  reason : {behavior.get('rulerReason') or row.get('llm', {}).get('rulerReason', '')}",
    f"  policy : {behavior.get('policySummary', '')}",
    f"  mood   : {behavior.get('crowdMoodDetail') or crowd.get('moodText', '')}",
    f"  react  : {behavior.get('eventReaction') or crowd.get('eventReaction', '')}",
    f"  rumor  : {crowd.get('rumor', '')}",
    f"  mascot : {speech}",
    f"  source : {crowd.get('source', '')} / {row.get('llm', {}).get('decisionSource', '')}",
  ]
  if opinion.get("active"):
    lines.append(f"  opinion: active trigger={opinion.get('trigger', [])}")
    for agent in opinion.get("agents") or []:
      lines.append(
        f"    - {agent.get('agentId')} [{agent.get('intent')}/{agent.get('mode')}] "
        f"panic={agent.get('panic')} {agent.get('rumor', '')}"
      )
  else:
    lines.append("  opinion: inactive")
  return "\n".join(lines)


def main() -> None:
  parser = argparse.ArgumentParser(description="Preview readable month log lines")
  parser.add_argument(
    "--log",
    required=True,
    help="Path to monthly JSONL (e.g. logs/runs/overnight_b_llm_1853.jsonl)",
  )
  parser.add_argument("--tail", type=int, default=DEFAULT_TAIL, help="How many recent months")
  parser.add_argument("--only-events", action="store_true", help="Only months with events")
  args = parser.parse_args()

  path = Path(args.log)
  rows = loadRows(path)
  if args.only_events:
    rows = [row for row in rows if row.get("events")]
  selected = rows[-args.tail :] if args.tail > 0 else rows
  print(f"log={path} showing={len(selected)}/{len(rows)}")
  for row in selected:
    print(formatRow(row))
    print()


if __name__ == "__main__":
  main()
