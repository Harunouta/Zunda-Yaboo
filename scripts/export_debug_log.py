"""Export LLM prompts and dialogue blocks from a monthly JSONL (local debug)."""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("export_speech_log", _SCRIPT_DIR / "export_speech_log.py")
_speechMod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_speechMod)
collectSpeechEvents = _speechMod.collectSpeechEvents
loadRows = _speechMod.loadRows

README_TEXT = (
  "Debug export: LLM prompts, behavior/crowd/opinion/agri blocks per month.\n"
  "Large. Local use only — not for public GitHub redistribution.\n"
)


def collectDebugRecord(row: dict) -> dict | None:
  llm = row.get("llm") or {}
  behavior = row.get("behavior") or {}
  crowd = row.get("crowd") or {}
  law = row.get("law") or {}
  opinion = row.get("opinionLeaders") or {}
  agri = row.get("agriLogistics") or {}
  leaderPrompt = str(llm.get("leaderPrompt") or "").strip()
  crowdPrompt = str(llm.get("crowdPrompt") or "").strip()
  hasPrompt = bool(leaderPrompt or crowdPrompt)
  hasSpeech = bool(collectSpeechEvents(row))
  hasAgents = bool((opinion.get("agents") or []) or (agri.get("agents") or []))
  if not hasPrompt and not hasSpeech and not hasAgents:
    return None
  return {
    "yearMonth": row.get("yearMonth"),
    "standard": row.get("monetaryStandard"),
    "events": [str(item) for item in (row.get("events") or []) if item != "riot_risk"],
    "llm": {
      "decisionSource": llm.get("decisionSource"),
      "historicalPolicy": llm.get("historicalPolicy"),
      "leaderPrompt": llm.get("leaderPrompt"),
      "crowdPrompt": llm.get("crowdPrompt"),
      "rulerReason": llm.get("rulerReason") or behavior.get("rulerReason"),
    },
    "law": {"decree": law.get("decree")},
    "behavior": behavior,
    "crowd": crowd,
    "opinionLeaders": opinion,
    "agriLogistics": agri,
  }


def buildDebugZip(logPath: Path) -> bytes:
  records: list[dict] = []
  for row in loadRows(logPath):
    record = collectDebugRecord(row)
    if record:
      records.append(record)
  jsonlBody = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records)
  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("debug_llm.jsonl", jsonlBody)
    archive.writestr("README.txt", README_TEXT)
  return buffer.getvalue()


def main() -> int:
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument("--log", required=True, type=Path)
  parser.add_argument("--out", type=Path, default=None)
  args = parser.parse_args()
  body = buildDebugZip(args.log)
  outPath = args.out or Path(str(args.log.with_suffix("")) + "_debug.zip")
  outPath.parent.mkdir(parents=True, exist_ok=True)
  outPath.write_bytes(body)
  rows = loadRows(args.log)
  records = sum(1 for row in rows if collectDebugRecord(row))
  print(f"months={len(rows)} debug_records={records} wrote {outPath} bytes={len(body)}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
