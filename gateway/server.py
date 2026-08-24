#!/usr/bin/env python3
"""Stdlib OpenAI-compatible proxy. Splits ruler JSON across LM Studio models."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

try:
  from split import (
    extractJsonObject,
    idsPrompt,
    isRulerRequest,
    mergeRulerParts,
    pickProseModel,
    policyPrompt,
    prosePrompt,
    specialistModels,
    userContent,
  )
except ImportError:
  from gateway.split import (  # type: ignore
    extractJsonObject,
    idsPrompt,
    isRulerRequest,
    mergeRulerParts,
    pickProseModel,
    policyPrompt,
    prosePrompt,
    specialistModels,
    userContent,
  )


LISTEN_HOST = os.getenv("GW_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("GW_LISTEN_PORT", "4000"))
UPSTREAM_HOST = os.getenv("GW_LMSTUDIO_HOST", os.getenv("LM_STUDIO_HOST", "host.docker.internal"))
UPSTREAM_PORT = int(os.getenv("GW_LMSTUDIO_PORT", os.getenv("LM_STUDIO_PORT", "1234")))
UPSTREAM_TIMEOUT = int(os.getenv("GW_UPSTREAM_TIMEOUT_SEC", "180"))
SPECIALIST_TIMEOUT = int(os.getenv("GW_SPECIALIST_TIMEOUT_SEC", "90"))
MAX_WORKERS = max(int(os.getenv("GW_MAX_WORKERS", "3")), 1)


def upstreamBase() -> str:
  return f"http://{UPSTREAM_HOST}:{UPSTREAM_PORT}"


def jsonBytes(payload: Any, status: int = 200) -> tuple[int, bytes, str]:
  body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
  return status, body, "application/json; charset=utf-8"


def readBody(handler: BaseHTTPRequestHandler) -> bytes:
  length = int(handler.headers.get("Content-Length") or 0)
  return handler.rfile.read(length) if length else b""


def proxyRaw(
  method: str,
  path: str,
  body: bytes,
  headers: dict[str, str],
  timeoutSec: int,
) -> tuple[int, bytes, str]:
  url = f"{upstreamBase()}{path}"
  requestHeaders = {"Content-Type": headers.get("Content-Type", "application/json")}
  auth = headers.get("Authorization")
  if auth:
    requestHeaders["Authorization"] = auth
  request = urllib.request.Request(
    url,
    data=body if method != "GET" else None,
    headers=requestHeaders,
    method=method,
  )
  try:
    with urllib.request.urlopen(request, timeout=timeoutSec) as response:
      payload = response.read()
      contentType = response.headers.get("Content-Type") or "application/json"
      return int(response.status), payload, contentType
  except urllib.error.HTTPError as error:
    return error.code, error.read(), error.headers.get("Content-Type") or "application/json"
  except urllib.error.URLError as error:
    status, payload, ctype = jsonBytes(
      {"error": {"message": f"upstream unreachable: {error}", "type": "gateway_error"}},
      502,
    )
    return status, payload, ctype


def chatUpstream(
  model: str,
  systemPrompt: str,
  userPrompt: str,
  temperature: float,
  maxTokens: int,
) -> dict[str, Any]:
  payload = {
    "model": model,
    "messages": [
      {
        "role": "system",
        "content": systemPrompt + " Respond with a single JSON object only. No markdown.",
      },
      {"role": "user", "content": userPrompt},
    ],
    "temperature": temperature,
    "stream": False,
    "max_tokens": maxTokens,
  }
  body = json.dumps(payload).encode("utf-8")
  status, raw, _ctype = proxyRaw(
    "POST",
    "/v1/chat/completions",
    body,
    {"Content-Type": "application/json"},
    SPECIALIST_TIMEOUT,
  )
  if status >= 400:
    raise ConnectionError(
      f"specialist {model} HTTP {status}: {raw.decode('utf-8', errors='replace')[:400]}"
    )
  parsed = json.loads(raw.decode("utf-8"))
  message = ((parsed.get("choices") or [{}])[0].get("message") or {})
  content = str(message.get("content") or "")
  if not content.strip():
    for key in ("reasoning_content", "reasoning", "thinking"):
      value = message.get(key) or ""
      if str(value).strip():
        content = str(value)
        break
  if not content.strip():
    raise ConnectionError(f"specialist {model} returned empty content")
  return extractJsonObject(content)


def completionEnvelope(model: str, content: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
  return {
    "id": "chatcmpl-zunda-gw",
    "object": "chat.completion",
    "created": int(time.time()),
    "model": model,
    "choices": [
      {
        "index": 0,
        "message": {"role": "assistant", "content": content},
        "finish_reason": "stop",
      }
    ],
    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    "gateway": extra or {},
  }


def splitRuler(body: dict[str, Any]) -> dict[str, Any]:
  messages = body.get("messages") or []
  if not isinstance(messages, list):
    messages = []
  userPrompt = userContent(messages)
  models = specialistModels()
  proseModel = pickProseModel(userPrompt)
  jobs = {
    "policy": (models["policy"],) + policyPrompt(userPrompt),
    "ids": (models["ids"],) + idsPrompt(userPrompt),
    "prose": (proseModel,) + prosePrompt(userPrompt),
  }
  results: dict[str, dict[str, Any] | None] = {"policy": None, "ids": None, "prose": None}
  errors: dict[str, str] = {}
  temperature = float(body.get("temperature") or 0.4)
  maxTokens = int(body.get("max_tokens") or 384)

  def runJob(name: str, model: str, systemPrompt: str, prompt: str) -> tuple[str, dict[str, Any]]:
    parsed = chatUpstream(model, systemPrompt, prompt, temperature, maxTokens)
    return name, parsed

  with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    futures = [
      pool.submit(runJob, name, model, systemPrompt, prompt)
      for name, (model, systemPrompt, prompt) in jobs.items()
    ]
    for future in as_completed(futures):
      try:
        name, parsed = future.result()
        results[name] = parsed
      except Exception as error:
        errors[str(error)] = str(error)

  for name, (model, _system, _prompt) in jobs.items():
    if results[name] is None:
      errors.setdefault(name, f"{name} via {model} failed")

  merged = mergeRulerParts(results["policy"], results["ids"], results["prose"])
  extra = {
    "split": True,
    "specialists": {
      "policy": jobs["policy"][0],
      "ids": jobs["ids"][0],
      "prose": jobs["prose"][0],
    },
    "errors": errors,
  }
  return completionEnvelope(
    str(body.get("model") or "zunda-ruler"),
    json.dumps(merged, ensure_ascii=False),
    extra,
  )


class GatewayHandler(BaseHTTPRequestHandler):
  protocol_version = "HTTP/1.1"

  def log_message(self, format: str, *args: Any) -> None:
    sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

  def _send(
    self,
    status: int,
    body: bytes,
    contentType: str,
    extraHeaders: dict[str, str] | None = None,
  ) -> None:
    self.send_response(status)
    self.send_header("Content-Type", contentType)
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Cache-Control", "no-store")
    self.send_header("X-Zunda-Gateway", "1")
    for key, value in (extraHeaders or {}).items():
      self.send_header(key, value)
    self.end_headers()
    self.wfile.write(body)

  def do_GET(self) -> None:
    parsed = urlparse(self.path)
    if parsed.path in ("/health", "/"):
      status, body, ctype = jsonBytes(
        {
          "ok": True,
          "service": "zunda-llm-gateway",
          "upstream": upstreamBase(),
          "specialists": specialistModels(),
        }
      )
      self._send(status, body, ctype)
      return
    if parsed.path in ("/v1/models", "/models"):
      status, raw, ctype = proxyRaw("GET", "/v1/models", b"", dict(self.headers), 15)
      if status >= 400:
        self._send(status, raw, ctype)
        return
      try:
        payload = json.loads(raw.decode("utf-8"))
      except json.JSONDecodeError:
        self._send(status, raw, ctype)
        return
      data = payload.get("data") if isinstance(payload, dict) else None
      if isinstance(data, list):
        ids = {str(item.get("id")) for item in data if isinstance(item, dict)}
        for alias in ("zunda-ruler", "qwen3.6-27b"):
          if alias not in ids:
            data.append({"id": alias, "object": "model", "owned_by": "zunda-gateway"})
        payload["data"] = data
      status, body, ctype = jsonBytes(payload)
      self._send(status, body, ctype)
      return
    self._send(404, b'{"error":"not found"}', "application/json")

  def do_POST(self) -> None:
    parsed = urlparse(self.path)
    raw = readBody(self)
    if parsed.path not in ("/v1/chat/completions", "/chat/completions"):
      self._send(404, b'{"error":"not found"}', "application/json")
      return
    try:
      body = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
      status, payload, ctype = jsonBytes({"error": {"message": "invalid json"}}, 400)
      self._send(status, payload, ctype)
      return
    if body.get("stream"):
      body["stream"] = False
    model = str(body.get("model") or "")
    messages = body.get("messages") if isinstance(body.get("messages"), list) else []
    if isRulerRequest(model, messages):
      try:
        payload = splitRuler(body)
        status, rawOut, ctype = jsonBytes(payload)
        self._send(status, rawOut, ctype)
      except Exception as error:
        status, rawOut, ctype = jsonBytes(
          {"error": {"message": str(error), "type": "gateway_split_error"}},
          502,
        )
        self._send(status, rawOut, ctype)
      return
    status, proxied, ctype = proxyRaw(
      "POST",
      "/v1/chat/completions",
      json.dumps(body).encode("utf-8"),
      dict(self.headers),
      UPSTREAM_TIMEOUT,
    )
    self._send(status, proxied, ctype)


def serve(host: str = LISTEN_HOST, port: int = LISTEN_PORT) -> ThreadingHTTPServer:
  server = ThreadingHTTPServer((host, port), GatewayHandler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  return server


def main() -> int:
  server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), GatewayHandler)
  print(
    f"zunda-llm-gateway listen={LISTEN_HOST}:{LISTEN_PORT} upstream={upstreamBase()}",
    flush=True,
  )
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\nstopped", flush=True)
  return 0


if __name__ == "__main__":
  if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
  raise SystemExit(main())
