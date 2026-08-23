"""Debug LM Studio chat errors."""

import json
import os
import urllib.error
import urllib.request

host = os.getenv("LM_STUDIO_HOST", "host.docker.internal")
port = os.getenv("LM_STUDIO_PORT", "1234")
model = os.getenv("CROWD_MODEL", "google/gemma-4-e4b")
url = f"http://{host}:{port}/v1/chat/completions"

variants = [
  {
    "name": "plain_text",
    "payload": {
      "model": model,
      "messages": [
        {
          "role": "user",
          "content": (
            'Reply JSON only: {"ok":true,"rumor":"x","anger":0.1,'
            '"hoarding":0.1,"riotRisk":0.05,"moodText":"ok","mascotSpeech":"テストなのだ"}'
          ),
        }
      ],
      "temperature": 0.2,
      "max_tokens": 120,
      "stream": False,
      "response_format": {"type": "text"},
    },
  },
  {
    "name": "no_format",
    "payload": {
      "model": model,
      "messages": [
        {
          "role": "user",
          "content": (
            'Reply JSON only: {"ok":true,"rumor":"x","anger":0.1,'
            '"hoarding":0.1,"riotRisk":0.05,"moodText":"ok","mascotSpeech":"テストなのだ"}'
          ),
        }
      ],
      "temperature": 0.2,
      "max_tokens": 120,
      "stream": False,
    },
  },
]

for variant in variants:
  body = json.dumps(variant["payload"]).encode("utf-8")
  request = urllib.request.Request(
    url,
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
  )
  try:
    with urllib.request.urlopen(request, timeout=120) as response:
      raw = json.loads(response.read().decode("utf-8"))
    content = raw["choices"][0]["message"]["content"]
    print(variant["name"], "OK len=", len(content or ""), "preview=", repr((content or "")[:200]))
  except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    print(variant["name"], "HTTP", error.code, detail[:500])
  except Exception as error:
    print(variant["name"], "ERR", error)
