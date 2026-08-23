#!/bin/bash
set -e
cd /workspace
python -m src.main --no-llm --standard zunda --start 1853-06 --end 1853-08
python -m src.main --no-llm --standard anko --start 1853-06 --end 1853-07
python -m src.main --no-llm --standard edo_metal --start 1853-06 --end 1853-07
python - <<'PY'
import json
from pathlib import Path
rows = [json.loads(line) for line in Path("logs/monthly_run.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
for row in rows[-5:]:
  crowd = row["crowd"]
  print(row["yearMonth"], row["monetaryStandard"], crowd.get("mascotId"), crowd.get("mascotSpeech"))
PY
