"""Summarize mascot smoke JSONL next to the repo logs folder."""

from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "logs" / "mascot_smoke_summary.txt"
src = root / "logs" / "llm_smoke_mascot.jsonl"
rows = [
  json.loads(line)
  for line in src.read_text(encoding="utf-8").splitlines()
  if line.strip()
]
lines = []
for row in rows:
  crowd = row["crowd"]
  lines.append(
    f"{row['yearMonth']} source={crowd.get('source')} "
    f"mascot={crowd.get('mascotId')} speech={crowd.get('mascotSpeech')}"
  )
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out.read_text(encoding="utf-8"))
