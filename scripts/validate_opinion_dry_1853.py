"""Validate opinion_dry_1853.jsonl expectations."""

import json
from pathlib import Path

rows = [
  json.loads(line)
  for line in Path("logs/runs/opinion_dry_1853.jsonl").read_text(encoding="utf-8").splitlines()
  if line.strip()
]
print("months", len(rows))
for row in rows:
  opinion = row.get("opinionLeaders") or {}
  active = opinion.get("active")
  count = len(opinion.get("agents") or [])
  mark = "*" if active else " "
  print(f"{mark} {row['yearMonth']} active={active} agents={count} trigger={opinion.get('trigger')}")

perry = next(row for row in rows if row["yearMonth"] == "1853-07")
assert perry["opinionLeaders"]["active"] is True
assert len(perry["opinionLeaders"]["agents"]) == 5
normal = next(row for row in rows if row["yearMonth"] == "1853-01")
assert normal["opinionLeaders"]["active"] is False

checkpoint = json.loads(Path("checkpoints/latest.json").read_text(encoding="utf-8"))
agents = (checkpoint.get("meta") or {}).get("agents") or []
assert len(agents) == 5
print("checkpoint agents", [item["agentId"] for item in agents])
print("ASSERT_OK")
