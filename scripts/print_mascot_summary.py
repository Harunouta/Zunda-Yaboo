import json
from pathlib import Path

out = Path(r"D:\Zunda-Yaboo\logs\mascot_smoke_summary.txt")
rows = [
  json.loads(line)
  for line in Path(r"D:\Zunda-Yaboo\logs\llm_smoke_mascot.jsonl").read_text(encoding="utf-8").splitlines()
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
