"""Viewer / process LLM settings. Not sim coefficients. Secrets stay under logs/."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "logs" / "viewer_settings.json"

ROLE_KEYS = ("ruler", "crowd", "mascot", "opinion", "agri")

DEFAULT_SETTINGS: dict[str, Any] = {
  "provider": "lmstudio",
  "lmStudioHost": os.getenv("LM_STUDIO_HOST", "host.docker.internal"),
  "lmStudioPort": int(os.getenv("LM_STUDIO_PORT", "1234")),
  "openaiBaseUrl": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
  "openaiApiKey": "",
  "roles": {
    "ruler": os.getenv("RULER_MODEL", "qwen3.6-27b"),
    "crowd": os.getenv("CROWD_MODEL", "qwen2.5-7b-instruct"),
    "mascot": os.getenv("MASCOT_MODEL", os.getenv("CROWD_MODEL", "qwen2.5-7b-instruct")),
    "opinion": os.getenv("OPINION_MODEL", os.getenv("CROWD_MODEL", "qwen2.5-7b-instruct")),
    "agri": os.getenv("AGRI_MODEL", os.getenv("CROWD_MODEL", "qwen2.5-7b-instruct")),
  },
}


def defaultSettings() -> dict[str, Any]:
  return json.loads(json.dumps(DEFAULT_SETTINGS))


def loadSettings() -> dict[str, Any]:
  merged = defaultSettings()
  if SETTINGS_PATH.is_file():
    try:
      raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
      if isinstance(raw, dict):
        merged.update({key: raw[key] for key in raw if key != "roles"})
        roles = dict(merged["roles"])
        incoming = raw.get("roles") or {}
        if isinstance(incoming, dict):
          roles.update(incoming)
        merged["roles"] = roles
    except (json.JSONDecodeError, OSError):
      pass
  return merged


def saveSettings(payload: dict[str, Any]) -> dict[str, Any]:
  current = loadSettings()
  provider = str(payload.get("provider") or current["provider"]).strip().lower()
  if provider not in ("lmstudio", "openai"):
    raise ValueError("provider must be lmstudio or openai")
  current["provider"] = provider
  if "lmStudioHost" in payload:
    current["lmStudioHost"] = str(payload.get("lmStudioHost") or "").strip() or current["lmStudioHost"]
  if "lmStudioPort" in payload:
    current["lmStudioPort"] = int(payload.get("lmStudioPort") or current["lmStudioPort"])
  if "openaiBaseUrl" in payload:
    current["openaiBaseUrl"] = str(payload.get("openaiBaseUrl") or current["openaiBaseUrl"]).strip()
  key = payload.get("openaiApiKey")
  if isinstance(key, str) and key.strip() and key.strip() != "********":
    current["openaiApiKey"] = key.strip()
  roles = dict(current["roles"])
  incomingRoles = payload.get("roles") or {}
  if isinstance(incomingRoles, dict):
    for role in ROLE_KEYS:
      if incomingRoles.get(role):
        roles[role] = str(incomingRoles[role]).strip()
  current["roles"] = roles
  SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
  SETTINGS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
  return current


def publicSettings() -> dict[str, Any]:
  data = loadSettings()
  key = str(data.get("openaiApiKey") or "")
  data["openaiApiKey"] = "********" if key else ""
  data["hasOpenaiKey"] = bool(key)
  data["splitPlan"] = gatewaySplitPlan(data.get("roles") or {})
  data["gatewayHint"] = (
    "ポート 4000 ならゲートウェイ経由。為政者は GUI 上1本でも、中で数値・ID・布告に分かれる。"
  )
  return data


def settingsEnv(data: dict[str, Any] | None = None) -> dict[str, str]:
  data = data or loadSettings()
  roles = data.get("roles") or {}
  env = {
    "LLM_PROVIDER": str(data.get("provider") or "lmstudio"),
    "LM_STUDIO_HOST": str(data.get("lmStudioHost") or "host.docker.internal"),
    "LM_STUDIO_PORT": str(int(data.get("lmStudioPort") or 1234)),
    "OPENAI_BASE_URL": str(data.get("openaiBaseUrl") or "https://api.openai.com/v1"),
    "RULER_MODEL": str(roles.get("ruler") or ""),
    "CROWD_MODEL": str(roles.get("crowd") or ""),
    "MASCOT_MODEL": str(roles.get("mascot") or roles.get("crowd") or ""),
    "OPINION_MODEL": str(roles.get("opinion") or roles.get("crowd") or ""),
    "AGRI_MODEL": str(roles.get("agri") or roles.get("crowd") or ""),
  }
  apiKey = str(data.get("openaiApiKey") or "")
  if apiKey:
    env["OPENAI_API_KEY"] = apiKey
  return env


GATEWAY_DOWNLOAD_LIST: list[dict[str, Any]] = [
  {
    "id": "google/gemma-4-e4b",
    "purpose": "opinion / agri / 政策の数値",
    "required": True,
  },
  {
    "id": "qwen2.5-7b-instruct",
    "purpose": "crowd / mascot / historicalPolicyIds",
    "required": True,
  },
  {
    "id": "qwen2.5-14b-instruct",
    "purpose": "平時の布告文と rulerReason",
    "required": True,
  },
  {
    "id": "qwen3.6-27b",
    "purpose": "飢饉・戦争など危機月の布告のみ（常時ロードしない）",
    "required": False,
  },
  {
    "id": "qwen3-4b-instruct-2507",
    "purpose": "政策の数値JSON（手持ちなら Gemma より軽く常駐しやすい）",
    "required": False,
  },
]


def gatewaySpecialistIds() -> dict[str, str]:
  return {
    "policy": os.getenv("GW_POLICY_MODEL", "qwen3-4b-instruct-2507").strip(),
    "ids": os.getenv("GW_IDS_MODEL", "qwen2.5-7b-instruct").strip(),
    "prose": os.getenv("GW_PROSE_MODEL", "qwen2.5-14b-instruct").strip(),
    "crisis": os.getenv("GW_CRISIS_MODEL", "qwen3.6-27b").strip(),
  }


def gatewaySplitPlan(
  roles: dict[str, Any] | None = None,
  installedIds: list[str] | None = None,
) -> list[dict[str, Any]]:
  roles = roles or {}
  specialists = gatewaySpecialistIds()
  installed = installedIds if installedIds is not None else []
  haveInventory = installedIds is not None

  def taskRow(taskId: str, label: str, modelId: str, how: str) -> dict[str, Any]:
    present, matchedId = modelIsInstalled(modelId, installed) if haveInventory else (None, "")
    return {
      "id": taskId,
      "label": label,
      "modelId": modelId,
      "how": how,
      "present": present,
      "matchedId": matchedId,
    }

  rulerModel = str(roles.get("ruler") or os.getenv("RULER_MODEL", "qwen3.6-27b"))
  return [
    {
      "lane": "ruler",
      "title": "為政者レーン",
      "simRole": "ruler",
      "simModel": rulerModel,
      "blurb": "シミュは ruler を1回だけ呼ぶ。ゲートウェイが中で仕事を分ける。",
      "tasks": [
        taskRow("policy", "税率・備蓄・藩札などの数値", specialists["policy"], "分解"),
        taskRow("ids", "historicalPolicyIds の選択", specialists["ids"], "分解"),
        taskRow("prose", "布告文と理由（平時）", specialists["prose"], "分解"),
        taskRow("crisis", "飢饉・戦争月の布告だけ", specialists["crisis"], "分解・危機月のみ"),
      ],
    },
    {
      "lane": "voices",
      "title": "市井レーン",
      "simRole": "",
      "simModel": "",
      "blurb": "分解しない。役のモデルへそのまま通す。",
      "tasks": [
        taskRow("crowd", "群衆・噂", str(roles.get("crowd") or "qwen2.5-7b-instruct"), "通す"),
        taskRow("mascot", "マスコット", str(roles.get("mascot") or roles.get("crowd") or "qwen2.5-7b-instruct"), "通す"),
        taskRow("opinion", "オピニオンリーダー", str(roles.get("opinion") or "google/gemma-4-e4b"), "通す"),
        taskRow("agri", "農・物流", str(roles.get("agri") or "google/gemma-4-e4b"), "通す"),
      ],
    },
  ]


def normalizeModelKey(modelId: str) -> str:
  text = (modelId or "").strip().lower().replace("_", "-")
  if "/" in text:
    text = text.rsplit("/", 1)[-1]
  if "@" in text:
    text = text.split("@", 1)[0]
  return text.strip()


def modelIsInstalled(wantedId: str, installedIds: list[str]) -> tuple[bool, str]:
  want = normalizeModelKey(wantedId)
  if not want:
    return False, ""
  for actual in installedIds:
    have = normalizeModelKey(actual)
    if not have:
      continue
    if want == have or have.endswith(want) or want.endswith(have):
      return True, str(actual)
  return False, ""


def annotateDownloadList(
  downloadList: list[dict[str, Any]],
  installedIds: list[str],
) -> list[dict[str, Any]]:
  annotated: list[dict[str, Any]] = []
  for item in downloadList:
    row = dict(item)
    present, matchedId = modelIsInstalled(str(row.get("id") or ""), installedIds)
    row["present"] = present
    row["matchedId"] = matchedId
    annotated.append(row)
  return annotated


def fetchModelIdsFromUrl(url: str, timeoutSec: float = 2.5) -> list[str]:
  request = urllib.request.Request(url, method="GET")
  with urllib.request.urlopen(request, timeout=timeoutSec) as response:
    payload = json.loads(response.read().decode("utf-8"))
  ids: list[str] = []
  for item in payload.get("data") or []:
    if isinstance(item, dict) and item.get("id"):
      modelId = str(item["id"])
      if modelId not in ids and modelId != "zunda-ruler":
        ids.append(modelId)
  return ids


def probeInstalledModelIds() -> tuple[list[str], str, str]:
  hosts: list[str] = []
  for host in (
    os.getenv("ZUNDA_GATEWAY_HOST", "host.docker.internal"),
    os.getenv("LM_STUDIO_HOST", "host.docker.internal"),
    "host.docker.internal",
    "127.0.0.1",
    "localhost",
  ):
    if host and host not in hosts:
      hosts.append(host)
  ports: list[int] = []
  for port in (
    int(os.getenv("ZUNDA_GATEWAY_PORT", "4000")),
    int(os.getenv("LM_STUDIO_PORT", "1234")),
    4000,
    1234,
  ):
    if port not in ports:
      ports.append(port)
  lastError = ""
  for port in ports:
    for host in hosts:
      url = f"http://{host}:{port}/v1/models"
      try:
        ids = fetchModelIdsFromUrl(url)
        if ids:
          return ids, f"{host}:{port}", ""
      except Exception as error:
        lastError = f"{url}: {error}"
  return [], "", lastError or "LM Studio / gateway に届かない"


def gatewayDefaultPreset() -> dict[str, Any]:
  return {
    "provider": "lmstudio",
    "lmStudioHost": os.getenv("ZUNDA_GATEWAY_HOST", "host.docker.internal"),
    "lmStudioPort": int(os.getenv("ZUNDA_GATEWAY_PORT", "4000")),
    "openaiBaseUrl": os.getenv(
      "ZUNDA_GATEWAY_OPENAI_URL",
      "http://host.docker.internal:4000/v1",
    ),
    "roles": {
      "ruler": os.getenv("RULER_MODEL", "qwen3.6-27b"),
      "crowd": "qwen2.5-7b-instruct",
      "mascot": "qwen2.5-7b-instruct",
      "opinion": "google/gemma-4-e4b",
      "agri": "google/gemma-4-e4b",
    },
    "downloadList": GATEWAY_DOWNLOAD_LIST,
  }


def gatewayDefaultWithInventory() -> dict[str, Any]:
  preset = gatewayDefaultPreset()
  installedIds, source, error = probeInstalledModelIds()
  downloadList = annotateDownloadList(list(preset["downloadList"]), installedIds)
  required = [item for item in downloadList if item.get("required")]
  optional = [item for item in downloadList if not item.get("required")]
  preset["downloadList"] = downloadList
  preset["installedIds"] = installedIds
  preset["probeSource"] = source
  preset["probeError"] = error
  preset["requiredPresent"] = sum(1 for item in required if item.get("present"))
  preset["requiredTotal"] = len(required)
  preset["optionalPresent"] = sum(1 for item in optional if item.get("present"))
  preset["optionalTotal"] = len(optional)
  preset["ready"] = bool(source) and all(item.get("present") for item in required)
  preset["splitPlan"] = gatewaySplitPlan(preset.get("roles") or {}, installedIds)
  return preset


def applyGatewayDefault() -> dict[str, Any]:
  preset = gatewayDefaultPreset()
  saveSettings({key: value for key, value in preset.items() if key != "downloadList"})
  public = publicSettings()
  public["appliedPreset"] = "gateway"
  public["downloadList"] = GATEWAY_DOWNLOAD_LIST
  return public
