"""Unit tests for the Docker LLM gateway. Does not start a full sim."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gateway"))

from split import (  # noqa: E402
  extractJsonObject,
  isCrisisPrompt,
  isRulerRequest,
  mergeRulerParts,
  pickProseModel,
)
from src import llm_settings  # noqa: E402


def assertTrue(condition: bool, message: str) -> None:
  if not condition:
    raise AssertionError(message)


def testExtractAndMerge() -> None:
  blob = 'preamble\n```json\n{"decree": "豆を守れ", "rulerReason": "蔵が薄い"}\n```'
  parsed = extractJsonObject(blob)
  assertTrue(parsed["decree"] == "豆を守れ", "extractJsonObject missed decree")
  merged = mergeRulerParts(
    {
      "policy": {"processBeansRatio": 0.8, "tradeStance": "limited"},
      "lawNumbers": {"taxRate": 0.2, "targetItem": "rice"},
    },
    {"historicalPolicyIds": ["tokugawa_rice_note", "extra", "keep", "drop"]},
    parsed,
  )
  assertTrue(merged["law"]["decree"] == "豆を守れ", "merge dropped decree")
  assertTrue(merged["law"]["taxRate"] == 0.2, "merge dropped taxRate")
  assertTrue(merged["policy"]["processBeansRatio"] == 0.8, "merge dropped policy")
  assertTrue(merged["historicalPolicyIds"] == ["tokugawa_rice_note", "extra", "keep"], "id cap is 3")
  assertTrue(merged["rulerReason"] == "蔵が薄い", "merge dropped rulerReason")
  fallback = mergeRulerParts(None, None, None)
  assertTrue(fallback["policy"]["tradeStance"] == "closed", "defaults missing")
  assertTrue(fallback["law"]["decree"] == "", "empty decree default")


def testRulerAndCrisis() -> None:
  assertTrue(isRulerRequest("qwen3.6-27b", []), "27b should split")
  assertTrue(isRulerRequest("zunda-ruler", []), "alias should split")
  assertTrue(
    isRulerRequest(
      "google/gemma-4-e4b",
      [{"role": "system", "content": "You are the Edo/modern Japanese ruler agent."}],
    ),
    "system prompt should split",
  )
  assertTrue(not isRulerRequest("qwen2.5-7b-instruct", [{"role": "user", "content": "hello"}]), "crowd must pass through")
  assertTrue(isCrisisPrompt("天明の飢饉で米が尽きた"), "famine is crisis")
  assertTrue(not isCrisisPrompt("平時の豊作である"), "peace is not crisis")
  os.environ["GW_CRISIS_USE_27B"] = "1"
  os.environ["GW_CRISIS_MODEL"] = "qwen3.6-27b"
  os.environ["GW_PROSE_MODEL"] = "qwen2.5-14b-instruct"
  assertTrue(pickProseModel("黒船が来航した") == "qwen3.6-27b", "crisis uses 27b")
  assertTrue(pickProseModel("例月の検地") == "qwen2.5-14b-instruct", "normal uses 14b")


def testGatewayPreset() -> None:
  preset = llm_settings.gatewayDefaultPreset()
  assertTrue(preset["provider"] == "lmstudio", "preset stays on lmstudio")
  assertTrue(int(preset["lmStudioPort"]) == 4000, "preset points at gateway port")
  assertTrue(preset["roles"]["opinion"] == "google/gemma-4-e4b", "opinion uses gemma")
  assertTrue(preset["roles"]["ruler"] == "qwen3.6-27b", "sim still asks for 27b; gateway splits")
  required = [item["id"] for item in preset["downloadList"] if item["required"]]
  assertTrue("qwen2.5-14b-instruct" in required, "14b is required for decree")
  found, matched = llm_settings.modelIsInstalled(
    "google/gemma-4-e4b",
    ["google/gemma-4-e4b", "qwen2.5-7b-instruct"],
  )
  assertTrue(found and matched == "google/gemma-4-e4b", "gemma should count as present")
  missing, _blank = llm_settings.modelIsInstalled("qwen2.5-14b-instruct", ["qwen2.5-7b-instruct"])
  assertTrue(not missing, "14b must not match 7b")
  rows = llm_settings.annotateDownloadList(preset["downloadList"], ["qwen2.5-7b-instruct", "qwen3-4b-instruct-2507"])
  byId = {item["id"]: item for item in rows}
  assertTrue(byId["qwen2.5-7b-instruct"]["present"] is True, "7b present")
  assertTrue(byId["qwen2.5-14b-instruct"]["present"] is False, "14b missing")
  assertTrue(byId["qwen3-4b-instruct-2507"]["present"] is True, "4b present")
  plan = llm_settings.gatewaySplitPlan(preset["roles"], ["qwen2.5-7b-instruct", "qwen2.5-14b-instruct"])
  assertTrue(plan[0]["lane"] == "ruler", "ruler lane first")
  taskIds = [task["id"] for task in plan[0]["tasks"]]
  assertTrue(taskIds == ["policy", "ids", "prose", "crisis"], "ruler is split into four jobs")
  assertTrue(plan[1]["lane"] == "voices", "voices lane second")


class FakeStudioHandler(BaseHTTPRequestHandler):
  protocol_version = "HTTP/1.1"

  def log_message(self, format: str, *args: object) -> None:
    return

  def _send(self, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_GET(self) -> None:
    if self.path.startswith("/v1/models"):
      self._send(
        {
          "data": [
            {"id": "google/gemma-4-e4b"},
            {"id": "qwen2.5-7b-instruct"},
            {"id": "qwen2.5-14b-instruct"},
          ]
        }
      )
      return
    self._send({"error": "nope"}, 404)

  def do_POST(self) -> None:
    length = int(self.headers.get("Content-Length") or 0)
    raw = self.rfile.read(length) if length else b"{}"
    body = json.loads(raw.decode("utf-8") or "{}")
    model = str(body.get("model") or "")
    if model == "pass-me":
      self._send(
        {
          "choices": [
            {"message": {"role": "assistant", "content": json.dumps({"rumor": "ok", "anger": 0.1})}}
          ]
        }
      )
      return
    if "gemma" in model or model.endswith("e4b"):
      content = {
        "policy": {"processBeansRatio": 0.66, "tradeStance": "limited"},
        "lawNumbers": {"taxRate": 0.15, "targetItem": "rice", "penalty": "fine"},
      }
    elif "7b" in model:
      content = {"historicalPolicyIds": ["hand_item_a"]}
    else:
      content = {"decree": "米を出せ", "rulerReason": "市が乾く"}
    self._send({"choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}]})


def startFakeStudio() -> ThreadingHTTPServer:
  server = ThreadingHTTPServer(("127.0.0.1", 0), FakeStudioHandler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  return server


def httpJson(url: str, payload: dict | None = None) -> dict:
  data = None if payload is None else json.dumps(payload).encode("utf-8")
  request = urllib.request.Request(url, data=data, method="GET" if payload is None else "POST")
  if payload is not None:
    request.add_header("Content-Type", "application/json")
  with urllib.request.urlopen(request, timeout=8) as response:
    return json.loads(response.read().decode("utf-8"))


def testGatewayHttp() -> None:
  upstream = startFakeStudio()
  upPort = int(upstream.server_address[1])
  os.environ["GW_LMSTUDIO_HOST"] = "127.0.0.1"
  os.environ["GW_LMSTUDIO_PORT"] = str(upPort)
  os.environ["GW_POLICY_MODEL"] = "google/gemma-4-e4b"
  os.environ["GW_IDS_MODEL"] = "qwen2.5-7b-instruct"
  os.environ["GW_PROSE_MODEL"] = "qwen2.5-14b-instruct"
  import importlib
  import server as gatewayServer

  importlib.reload(gatewayServer)
  gateway = gatewayServer.serve("127.0.0.1", 0)
  time.sleep(0.2)
  gwPort = int(gateway.server_address[1])
  try:
    health = httpJson(f"http://127.0.0.1:{gwPort}/health")
    assertTrue(health.get("ok") is True, "health failed")
    models = httpJson(f"http://127.0.0.1:{gwPort}/v1/models")
    ids = [item.get("id") for item in models.get("data") or []]
    assertTrue("zunda-ruler" in ids, "alias missing from /v1/models")
    passed = httpJson(
      f"http://127.0.0.1:{gwPort}/v1/chat/completions",
      {
        "model": "pass-me",
        "messages": [{"role": "user", "content": "crowd"}],
      },
    )
    passedText = passed["choices"][0]["message"]["content"]
    assertTrue("rumor" in passedText, "pass-through failed")
    split = httpJson(
      f"http://127.0.0.1:{gwPort}/v1/chat/completions",
      {
        "model": "qwen3.6-27b",
        "messages": [{"role": "user", "content": "例月。係数手札 hand_item_a"}],
      },
    )
    merged = json.loads(split["choices"][0]["message"]["content"])
    assertTrue(merged["law"]["decree"] == "米を出せ", "split decree missing")
    assertTrue(merged["policy"]["processBeansRatio"] == 0.66, "split policy missing")
    assertTrue(merged["historicalPolicyIds"] == ["hand_item_a"], "split ids missing")
    assertTrue(split.get("gateway", {}).get("split") is True, "gateway meta missing")
  finally:
    gateway.shutdown()
    upstream.shutdown()


def main() -> int:
  testExtractAndMerge()
  testRulerAndCrisis()
  testGatewayPreset()
  testGatewayHttp()
  print("llm-gateway tests passed")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
