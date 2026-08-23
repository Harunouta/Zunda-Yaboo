"""Inspect raw LM Studio message fields for ruler model."""

import json
import os
import urllib.request

host = os.getenv("LM_STUDIO_HOST", "host.docker.internal")
port = os.getenv("LM_STUDIO_PORT", "1234")
model = os.getenv("RULER_MODEL", "qwen3.6-27b")
url = f"http://{host}:{port}/v1/chat/completions"
payload = {
  "model": model,
  "messages": [
    {"role": "system", "content": "Output JSON only."},
    {
      "role": "user",
      "content": (
        'Return JSON: {"law":{"decree":"テスト","targetItem":"zundaNotes",'
        '"taxRate":0.1,"penalty":"fine","enforcementBudget":10},'
        '"policy":{"processBeansRatio":0.5}}'
      ),
    },
  ],
  "temperature": 0.2,
  "max_tokens": 800,
  "stream": False,
}
body = json.dumps(payload).encode("utf-8")
request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(request, timeout=180) as response:
  raw = json.loads(response.read().decode("utf-8"))
choice = raw["choices"][0]
print(json.dumps(choice, ensure_ascii=False, indent=2)[:2000])
