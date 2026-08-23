"""Print last log crowd mascot fields."""

import json
from pathlib import Path

path = Path("/workspace/logs/monthly_run.jsonl")
lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
entry = json.loads(lines[-1])
crowd = entry.get("crowd", {})
print("yearMonth=", entry.get("yearMonth"))
print("mascotId=", crowd.get("mascotId"))
print("mascotSpeech=", crowd.get("mascotSpeech"))
print("source=", crowd.get("source"))
