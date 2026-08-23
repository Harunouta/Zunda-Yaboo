"""Export character / ruler speech lines from a monthly JSONL into readable logs.

Writes:
  - *.speech.md   (human-readable transcript)
  - *.speech.jsonl (one speech event per line)

Examples:
  python scripts/export_speech_log.py --log logs/runs/zunda_full_1603_2026.jsonl
  python scripts/export_speech_log.py --log logs/runs/overnight_b_llm_1853.jsonl --only-events
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def loadRows(path: Path) -> list[dict]:
  return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def collectSpeechEvents(row: dict) -> list[dict]:
  yearMonth = str(row.get("yearMonth") or "")
  events = [str(item) for item in (row.get("events") or []) if item != "riot_risk"]
  crowd = row.get("crowd") or {}
  behavior = row.get("behavior") or {}
  law = row.get("law") or {}
  llm = row.get("llm") or {}
  opinion = row.get("opinionLeaders") or {}
  out: list[dict] = []

  decree = str(law.get("decree") or "").strip()
  if decree:
    out.append({
      "yearMonth": yearMonth,
      "speaker": "ruler",
      "kind": "decree",
      "text": decree,
      "source": llm.get("decisionSource") or row.get("decisionSource") or "",
      "events": events,
    })

  reason = str(behavior.get("rulerReason") or llm.get("rulerReason") or "").strip()
  if reason:
    out.append({
      "yearMonth": yearMonth,
      "speaker": "ruler",
      "kind": "reason",
      "text": reason,
      "source": llm.get("decisionSource") or "",
      "events": events,
    })

  for agent in opinion.get("agents") or []:
    rumor = str(agent.get("rumor") or "").strip()
    if not rumor:
      continue
    out.append({
      "yearMonth": yearMonth,
      "speaker": str(agent.get("agentId") or "opinion"),
      "kind": "opinion",
      "text": rumor,
      "source": str(agent.get("source") or ""),
      "intent": agent.get("intent"),
      "mode": agent.get("mode"),
      "events": events,
    })

  speech = str(behavior.get("mascotSpeech") or crowd.get("mascotSpeech") or "").strip()
  if speech:
    out.append({
      "yearMonth": yearMonth,
      "speaker": str(crowd.get("mascotId") or "mascot"),
      "kind": "mascot",
      "text": speech,
      "source": str(crowd.get("source") or ""),
      "events": events,
    })
  return out


def toMarkdown(events: list[dict]) -> str:
  lines = ["# Speech transcript", ""]
  currentMonth = None
  for item in events:
    if item["yearMonth"] != currentMonth:
      currentMonth = item["yearMonth"]
      eventLabel = ", ".join(item.get("events") or []) or "—"
      lines.append(f"## {currentMonth}  ({eventLabel})")
      lines.append("")
    speaker = item["speaker"]
    kind = item["kind"]
    source = item.get("source") or ""
    extra = ""
    if item.get("intent"):
      extra = f" [{item.get('intent')}/{item.get('mode')}]"
    lines.append(f"- **{speaker}** ({kind}{extra}) {source}")
    lines.append(f"  - {item['text']}")
    lines.append("")
  return "\n".join(lines)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--log", required=True, type=Path)
  parser.add_argument("--out-prefix", type=Path, default=None, help="Default: same stem as --log")
  parser.add_argument("--only-events", action="store_true")
  parser.add_argument("--kinds", default="decree,mascot,opinion,reason", help="Comma list")
  args = parser.parse_args()

  wanted = {part.strip() for part in args.kinds.split(",") if part.strip()}
  rows = loadRows(args.log)
  if args.only_events:
    rows = [row for row in rows if any(e != "riot_risk" for e in (row.get("events") or []))]

  events: list[dict] = []
  for row in rows:
    for item in collectSpeechEvents(row):
      if item["kind"] in wanted:
        events.append(item)

  prefix = args.out_prefix or args.log.with_suffix("")
  mdPath = Path(str(prefix) + ".speech.md")
  jsonlPath = Path(str(prefix) + ".speech.jsonl")
  mdPath.parent.mkdir(parents=True, exist_ok=True)

  mdPath.write_text(toMarkdown(events), encoding="utf-8")
  with jsonlPath.open("w", encoding="utf-8") as handle:
    for item in events:
      handle.write(json.dumps(item, ensure_ascii=False) + "\n")

  byKind = {}
  for item in events:
    byKind[item["kind"]] = byKind.get(item["kind"], 0) + 1
  print(f"speech_events={len(events)} byKind={byKind}")
  print(f"wrote {mdPath}")
  print(f"wrote {jsonlPath}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
