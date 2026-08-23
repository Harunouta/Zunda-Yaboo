"""Minimal LM Studio chat test without response_format."""

import json
import urllib.request

payload = {
  "model": "google/gemma-4-e4b",
  "messages": [
    {"role": "system", "content": "Reply with JSON only."},
    {
      "role": "user",
      "content": '{"rumor":"x","anger":0.2,"hoarding":0.1,"riotRisk":0.1,"moodText":"ok","mascotSpeech":"テストなのだ"} と同じ形で短く返して',
    },
  ],
  "temperature": 0.2,
  "stream": False,
  "max_tokens": 200,
}
body = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
  "http://localhost:1234/v1/chat/completions",
  data=body,
  headers={"Content-Type": "application/json"},
  method="POST",
)
with urllib.request.urlopen(req, timeout=120) as resp:
  raw = json.loads(resp.read().decode("utf-8"))
print(raw["choices"][0]["message"]["content"][:1000])
