"""Quick LM Studio connectivity smoke."""

import json
import urllib.request

payload = {
  "model": "google/gemma-4-e4b",
  "messages": [
    {
      "role": "user",
      "content": (
        'Reply with JSON only: '
        '{"rumor":"test","anger":0.1,"hoarding":0.1,"riotRisk":0.05,"moodText":"ok"}'
      ),
    }
  ],
  "temperature": 0.2,
  "stream": False,
  "max_tokens": 150,
  "response_format": {"type": "json_object"},
}
body = json.dumps(payload).encode("utf-8")
request = urllib.request.Request(
  "http://localhost:1234/v1/chat/completions",
  data=body,
  headers={"Content-Type": "application/json"},
  method="POST",
)
with urllib.request.urlopen(request, timeout=90) as response:
  raw = json.loads(response.read().decode("utf-8"))
print(raw["choices"][0]["message"]["content"][:800])
