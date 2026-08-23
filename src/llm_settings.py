"""Viewer / process LLM settings. Not sim coefficients. Secrets stay under logs/."""

from __future__ import annotations

import json
import os
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
