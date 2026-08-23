"""LM Studio client — ruler (Qwen) + crowd/mascot (Gemma). Optional local models under ZUNDA_AI_DIR."""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from src.law_and_policy import RulerDecision, parseRulerDecision
from src.mascot import emptyMascotFields, systemPromptForMascot


DEFAULT_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))
RULER_MODEL = os.getenv("RULER_MODEL", "qwen3.6-27b")
CROWD_MODEL = os.getenv("CROWD_MODEL", "qwen2.5-7b-instruct")
# Optional second crowd model (LM Studio id). Tried after CROWD_MODEL fails JSON/empty.
CROWD_FALLBACK_MODEL = os.getenv("CROWD_FALLBACK_MODEL", "google/gemma-4-e4b").strip()
ZUNDA_AI_DIR = os.getenv("ZUNDA_AI_DIR", "").strip() or (
  "/models" if os.path.isdir("/models") else ""
)
DEFAULT_TIMEOUT = int(os.getenv("LM_TIMEOUT_SEC", "90"))
DEFAULT_MAX_TOKENS = int(os.getenv("LM_MAX_TOKENS", "512"))
CROWD_MAX_TOKENS = int(os.getenv("LM_CROWD_MAX_TOKENS", "768"))
RECAP_MAX_TOKENS = int(os.getenv("LM_RECAP_MAX_TOKENS", "2048"))
OPINION_MAX_TOKENS = int(os.getenv("LM_OPINION_MAX_TOKENS", "384"))
USE_JSON_SCHEMA = os.getenv("LM_USE_JSON_SCHEMA", "0").strip().lower() in ("1", "true", "yes", "on")
CHAT_RETRIES = max(int(os.getenv("LM_CHAT_RETRIES", "2")), 1)


RULER_SCHEMA: dict[str, Any] = {
  "type": "object",
  "properties": {
    "law": {
      "type": "object",
      "properties": {
        "decree": {"type": "string"},
        "targetItem": {"type": "string"},
        "taxRate": {"type": "number"},
        "penalty": {"type": "string"},
        "enforcementBudget": {"type": "number"},
        "durationTurns": {"type": "number"},
      },
      "required": ["decree", "targetItem", "taxRate", "penalty", "enforcementBudget"],
    },
    "policy": {
      "type": "object",
      "properties": {
        "processBeansRatio": {"type": "number"},
        "investSugarImport": {"type": "number"},
        "reserveReleaseRatio": {"type": "number"},
        "reserveMintingRatio": {"type": "number"},
        "tradeStance": {"type": "string"},
        "sugarSubsidy": {"type": "number"},
        "enforcementPriority": {"type": "number"},
        "blackMarketCrackdown": {"type": "number"},
        "foodRationPriority": {"type": "string"},
        "distributionBudgetRatio": {"type": "number"},
        "bureaucracyEfficiency": {"type": "number"},
        "hanSatsuIssueRatio": {"type": "number"},
        "goldSilverTargetRatio": {"type": "number"},
      },
      "required": ["processBeansRatio"],
    },
    "historicalPolicyIds": {"type": "array", "items": {"type": "string"}},
    "rulerReason": {"type": "string"},
  },
  "required": ["law", "policy"],
}

CROWD_SCHEMA: dict[str, Any] = {
  "type": "object",
  "properties": {
    "rumor": {"type": "string"},
    "anger": {"type": "number"},
    "hoarding": {"type": "number"},
    "riotRisk": {"type": "number"},
    "moodText": {"type": "string"},
    "mascotSpeech": {"type": "string"},
    "crowdMoodDetail": {"type": "string"},
    "eventReaction": {"type": "string"},
  },
  "required": ["rumor", "anger", "hoarding", "riotRisk", "moodText"],
}

OPINION_SCHEMA: dict[str, Any] = {
  "type": "object",
  "properties": {
    "panic": {"type": "number"},
    "rumor": {"type": "string"},
    "intent": {"type": "string"},
    "localBias": {"type": "string"},
  },
  "required": ["panic", "rumor", "intent", "localBias"],
}

AGRI_SCHEMA: dict[str, Any] = {
  "type": "object",
  "properties": {
    "effort": {"type": "number"},
    "blackMarketLeak": {"type": "number"},
    "stance": {"type": "string"},
    "rumor": {"type": "string"},
  },
  "required": ["effort", "blackMarketLeak", "stance", "rumor"],
}

AGRI_MAX_TOKENS = int(os.getenv("LM_AGRI_MAX_TOKENS", "256"))
VALID_OPINION_INTENTS = frozenset({"comply", "hoard", "flee", "black_market", "organize"})


def resolveLmHost(preferred: str | None = None, port: int = DEFAULT_PORT) -> str:
  candidates: list[str] = []
  if preferred:
    candidates.append(preferred)
  envHost = os.getenv("LM_STUDIO_HOST")
  if envHost:
    candidates.append(envHost)
  candidates.extend(["host.docker.internal", "172.17.0.1", "localhost", "127.0.0.1"])
  seen: set[str] = set()
  for host in candidates:
    if host in seen:
      continue
    seen.add(host)
    try:
      urllib.request.urlopen(f"http://{host}:{port}/v1/models", timeout=2)
      return host
    except Exception:
      continue
  return candidates[0] if candidates else "host.docker.internal"


DEFAULT_HOST = resolveLmHost()


def buildApiUrl(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
  provider = os.getenv("LLM_PROVIDER", "lmstudio").strip().lower()
  if provider == "openai":
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return f"{base}/chat/completions"
  return f"http://{host}:{port}/v1/chat/completions"


def modelForRole(role: str) -> str:
  roleKey = role.strip().lower()
  envName = {
    "ruler": "RULER_MODEL",
    "crowd": "CROWD_MODEL",
    "mascot": "MASCOT_MODEL",
    "opinion": "OPINION_MODEL",
    "agri": "AGRI_MODEL",
  }.get(roleKey, "CROWD_MODEL")
  fallback = RULER_MODEL if roleKey == "ruler" else CROWD_MODEL
  return os.getenv(envName, fallback) or fallback


def listLocalModelHints() -> list[str]:
  if not os.path.isdir(ZUNDA_AI_DIR):
    return []
  hints: list[str] = []
  for name in os.listdir(ZUNDA_AI_DIR):
    path = os.path.join(ZUNDA_AI_DIR, name)
    if os.path.isdir(path) or name.endswith((".gguf", ".bin")):
      hints.append(name)
  return hints


def _repairJsonText(text: str) -> str:
  cleaned = text.strip()
  cleaned = cleaned.replace("\ufeff", "")
  cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"')
  cleaned = cleaned.replace("\u2018", "'").replace("\u2019", "'")
  # Trailing commas before } or ]
  cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
  # Python-ish True/False/None that small models sometimes emit
  cleaned = re.sub(r"\bTrue\b", "true", cleaned)
  cleaned = re.sub(r"\bFalse\b", "false", cleaned)
  cleaned = re.sub(r"\bNone\b", "null", cleaned)
  return cleaned


def extractJsonObject(text: str) -> dict[str, Any]:
  text = _repairJsonText(text)
  if text.startswith("```"):
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
  text = text.strip()

  candidates: list[str] = [text]
  # Balanced-ish outer object (greedy last brace span)
  braceMatch = re.search(r"\{[\s\S]*\}", text)
  if braceMatch:
    candidates.append(braceMatch.group(0))
  # Nested-tolerant shallow objects
  candidates.extend(
    match.group(0)
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
  )

  lastError: Exception | None = None
  seen: set[str] = set()
  for candidate in candidates:
    repaired = _repairJsonText(candidate)
    if repaired in seen:
      continue
    seen.add(repaired)
    try:
      parsed = json.loads(repaired)
      if isinstance(parsed, dict):
        return parsed
      if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed[0]
    except json.JSONDecodeError as error:
      lastError = error
  if lastError:
    raise lastError
  raise json.JSONDecodeError("No JSON object found", text, 0)


def _messageText(message: dict[str, Any]) -> str:
  content = message.get("content") or ""
  if str(content).strip():
    return str(content)
  # Qwen-style reasoning models may put the answer only in reasoning_content.
  for key in ("reasoning_content", "reasoning", "thinking"):
    value = message.get(key) or ""
    if str(value).strip():
      return str(value)
  return ""


def callChat(
  userPrompt: str,
  systemPrompt: str,
  model: str,
  temperature: float = 0.7,
  jsonSchema: dict[str, Any] | None = None,
  host: str | None = None,
  port: int = DEFAULT_PORT,
  timeoutSec: int = DEFAULT_TIMEOUT,
  maxTokens: int | None = None,
) -> dict[str, Any]:
  activeHost = host or resolveLmHost()
  tokenBudget = DEFAULT_MAX_TOKENS if maxTokens is None else maxTokens
  lastError: Exception | None = None

  for attempt in range(CHAT_RETRIES):
    attemptTemp = temperature if attempt == 0 else min(temperature, 0.4)
    retryHint = ""
    if attempt > 0:
      retryHint = " RETRY: output ONLY one minified JSON object. No prose before or after."
    payload: dict[str, Any] = {
      "model": model,
      "messages": [
        {
          "role": "system",
          "content": (
            systemPrompt
            + " Respond with a single JSON object only. No markdown."
            + retryHint
          ),
        },
        {"role": "user", "content": userPrompt},
      ],
      "temperature": attemptTemp,
      "stream": False,
      "max_tokens": tokenBudget,
    }
    # Optional structured output — some LM Studio builds accept json_schema, not json_object.
    if USE_JSON_SCHEMA and jsonSchema is not None:
      payload["response_format"] = {
        "type": "json_schema",
        "json_schema": {
          "name": "zunda_payload",
          "strict": False,
          "schema": jsonSchema,
        },
      }

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    apiKey = os.getenv("OPENAI_API_KEY", "").strip()
    if os.getenv("LLM_PROVIDER", "lmstudio").strip().lower() == "openai" and apiKey:
      headers["Authorization"] = f"Bearer {apiKey}"
    request = urllib.request.Request(
      buildApiUrl(activeHost, port),
      data=body,
      headers=headers,
      method="POST",
    )
    try:
      with urllib.request.urlopen(request, timeout=timeoutSec) as response:
        raw = json.loads(response.read().decode("utf-8"))
      message = raw["choices"][0]["message"]
      content = _messageText(message)
      if not content.strip():
        raise ConnectionError(
          f"LM Studio returned empty content from {model} at {buildApiUrl(activeHost, port)}"
        )
      return extractJsonObject(content)
    except urllib.error.HTTPError as error:
      detail = error.read().decode("utf-8", errors="replace")
      # If schema mode is rejected, fall back to plain chat on next attempt.
      if USE_JSON_SCHEMA and jsonSchema is not None and error.code == 400:
        jsonSchema = None
      lastError = ConnectionError(
        f"LM Studio HTTP {error.code} at {buildApiUrl(activeHost, port)}: {detail}"
      )
    except urllib.error.URLError as error:
      lastError = ConnectionError(
        f"LM Studio unreachable at {buildApiUrl(activeHost, port)}: {error}"
      )
    except Exception as error:
      lastError = error

  assert lastError is not None
  raise lastError


def crowdModelChain() -> list[str]:
  models: list[str] = []
  for name in (
    modelForRole("crowd"),
    os.getenv("CROWD_FALLBACK_MODEL", CROWD_FALLBACK_MODEL),
    modelForRole("ruler"),
  ):
    if name and name not in models:
      models.append(name)
  return models


def modelsForRole(role: str) -> list[str]:
  models: list[str] = []
  primary = modelForRole(role)
  if primary:
    models.append(primary)
  for name in crowdModelChain():
    if name and name not in models:
      models.append(name)
  return models


def callRuler(userPrompt: str) -> tuple[RulerDecision, dict[str, Any]]:
  systemPrompt = (
    "You are the Edo/modern Japanese ruler agent. "
    "Invent law and policy freely. You hear farmers, millers, and shippers. "
    "Output JSON with law, policy, optional rulerReason. "
    "historicalPolicyIds picks up to 3 coefficient items from the monthly hand. "
    "Empty array is normal. Items twist inflation-brake vs growth for several months. "
    "law.decree must be Japanese, short, and readable — avoid bland boilerplate. "
    "rulerReason is one witty or tense Japanese sentence explaining the decree."
  )
  models = modelsForRole("ruler")
  lastError: Exception | None = None
  for model in models:
    try:
      raw = callChat(userPrompt, systemPrompt, model, jsonSchema=RULER_SCHEMA)
      decision = parseRulerDecision(raw)
      meta = {
        "rulerReason": str(raw.get("rulerReason") or raw.get("reason") or ""),
      }
      return decision, meta
    except Exception as error:
      lastError = error
  assert lastError is not None
  raise lastError


def callCrowd(userPrompt: str, mascotId: str | None = None) -> dict[str, Any]:
  if mascotId:
    systemPrompt = systemPromptForMascot(mascotId)
  else:
    systemPrompt = (
      "You are commoners and rumor-mongers in historical Japan. "
      "Output JSON: rumor, anger, hoarding, riotRisk, moodText, "
      "crowdMoodDetail, eventReaction. "
      "mascotSpeech should be an empty string. "
      "Make rumor concrete (shop, warehouse, street). No empty platitudes."
    )
  lastError: Exception | None = None
  raw: dict[str, Any] | None = None
  usedModel = modelForRole("mascot") if mascotId else modelForRole("crowd")
  for model in modelsForRole("mascot" if mascotId else "crowd"):
    try:
      raw = callChat(
        userPrompt,
        systemPrompt,
        model,
        temperature=0.7,
        jsonSchema=CROWD_SCHEMA,
        maxTokens=CROWD_MAX_TOKENS,
      )
      usedModel = model
      break
    except Exception as error:
      lastError = error
  if raw is None:
    assert lastError is not None
    raise lastError

  result = {
    "rumor": str(raw.get("rumor", "")),
    "anger": float(max(min(raw.get("anger", 0.2), 1.0), 0.0)),
    "hoarding": float(max(min(raw.get("hoarding", 0.1), 1.0), 0.0)),
    "riotRisk": float(max(min(raw.get("riotRisk", 0.05), 1.0), 0.0)),
    "moodText": str(raw.get("moodText", "")),
    "crowdMoodDetail": str(raw.get("crowdMoodDetail", "")),
    "eventReaction": str(raw.get("eventReaction", "")),
    "mascotId": mascotId,
    "mascotSpeech": str(raw.get("mascotSpeech", "")),
    "modelUsed": usedModel,
  }
  if mascotId is None:
    result.update(emptyMascotFields())
  elif not result["mascotSpeech"]:
    result["mascotSpeech"] = str(raw.get("moodText", ""))
  if not result["crowdMoodDetail"]:
    result["crowdMoodDetail"] = result["moodText"]
  if not result["eventReaction"]:
    result["eventReaction"] = result["rumor"] or result["moodText"]
  return result


def callOpinionLeader(userPrompt: str, agentId: str, role: str = "") -> dict[str, Any]:
  """Short JSON for one opinion leader (Gemma / CROWD_MODEL)."""
  roleBit = role or agentId
  systemPrompt = (
    f"You are {roleBit} ({agentId}), a biased opinion leader in historical Japan. "
    "You only know fragments and rumors — never invent national warehouse totals. "
    "Output JSON keys: panic (0-1), rumor (concrete Japanese), "
    "intent (comply|hoard|flee|black_market|organize), localBias (short Japanese). "
    "Keep rumor to one vivid sentence."
  )
  lastError: Exception | None = None
  raw: dict[str, Any] | None = None
  for model in modelsForRole("opinion"):
    try:
      raw = callChat(
        userPrompt,
        systemPrompt,
        model,
        temperature=0.7,
        jsonSchema=OPINION_SCHEMA,
        maxTokens=OPINION_MAX_TOKENS,
      )
      break
    except Exception as error:
      lastError = error
  if raw is None:
    assert lastError is not None
    raise lastError

  intent = str(raw.get("intent", "comply")).strip().lower().replace(" ", "_")
  if intent not in VALID_OPINION_INTENTS:
    intent = "comply"
  return {
    "panic": float(max(min(raw.get("panic", 0.3), 1.0), 0.0)),
    "rumor": str(raw.get("rumor", "")),
    "intent": intent,
    "localBias": str(raw.get("localBias", "")),
  }


def callAgriAgent(userPrompt: str, displayName: str, roleId: str) -> dict[str, Any]:
  systemPrompt = (
    f"You are {displayName}, a {roleId} in historical-to-modern Japan. "
    "Work from local feeling only. Output JSON: effort (0.35-1.45), "
    "blackMarketLeak (0-1), stance (short tag), rumor (one Japanese sentence)."
  )
  lastError: Exception | None = None
  raw: dict[str, Any] | None = None
  for model in modelsForRole("agri"):
    try:
      raw = callChat(
        userPrompt,
        systemPrompt,
        model,
        temperature=0.75,
        jsonSchema=AGRI_SCHEMA,
        maxTokens=AGRI_MAX_TOKENS,
      )
      break
    except Exception as error:
      lastError = error
  if raw is None:
    assert lastError is not None
    raise lastError
  return {
    "effort": float(raw.get("effort", 1.0)),
    "blackMarketLeak": float(raw.get("blackMarketLeak", 0.0)),
    "stance": str(raw.get("stance") or "fair"),
    "rumor": str(raw.get("rumor") or ""),
  }


def probeModels() -> dict[str, Any]:
  provider = os.getenv("LLM_PROVIDER", "lmstudio").strip().lower()
  port = int(os.getenv("LM_STUDIO_PORT", "1234"))
  host = resolveLmHost(port=port)
  if provider == "openai":
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/models"
    headers = {"Content-Type": "application/json"}
    apiKey = os.getenv("OPENAI_API_KEY", "").strip()
    if apiKey:
      headers["Authorization"] = f"Bearer {apiKey}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=15) as response:
      data = json.loads(response.read().decode("utf-8"))
    ids = [item.get("id") for item in (data.get("data") or []) if item.get("id")]
    return {
      "provider": "openai",
      "openai": {"modelIds": ids[:80]},
      "resolvedHost": base,
      "roles": {role: modelForRole(role) for role in ("ruler", "crowd", "mascot", "opinion", "agri")},
    }
  url = f"http://{host}:{port}/v1/models"
  request = urllib.request.Request(url, method="GET")
  with urllib.request.urlopen(request, timeout=10) as response:
    data = json.loads(response.read().decode("utf-8"))
  return {
    "provider": "lmstudio",
    "lmStudio": data,
    "resolvedHost": host,
    "localHints": listLocalModelHints(),
    "roles": {role: modelForRole(role) for role in ("ruler", "crowd", "mascot", "opinion", "agri")},
    "crowdFallbackModel": CROWD_FALLBACK_MODEL or None,
    "crowdModelChain": crowdModelChain(),
    "useJsonSchema": USE_JSON_SCHEMA,
    "zundaAiDir": ZUNDA_AI_DIR,
  }


RECAP_SCHEMA: dict[str, Any] = {
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "recap": {"type": "string"},
  },
  "required": ["recap"],
}


def callLifeRecap(userPrompt: str, mascotId: str | None) -> dict[str, Any]:
  if mascotId:
    systemPrompt = (
      systemPromptForMascot(mascotId)
      + " いまは月次の一言ではなく、その期間を暮らした総括を長く書いてよい。"
      " JSON は title と recap のみ。recap は日本語で複数段落。"
    )
  else:
    systemPrompt = (
      "You are an ordinary townsperson who lived through this whole period in Japan. "
      "Write a long Japanese memoir of how daily life, food, money, and fear changed. "
      "JSON keys only: title, recap. recap may be many paragraphs. No mascot speech endings."
    )
  lastError: Exception | None = None
  raw: dict[str, Any] | None = None
  usedModel = modelForRole("mascot") if mascotId else modelForRole("crowd")
  for model in modelsForRole("mascot" if mascotId else "crowd"):
    try:
      raw = callChat(
        userPrompt,
        systemPrompt,
        model,
        temperature=0.75,
        jsonSchema=RECAP_SCHEMA,
        maxTokens=RECAP_MAX_TOKENS,
      )
      usedModel = model
      break
    except Exception as error:
      lastError = error
  if raw is None:
    assert lastError is not None
    raise lastError
  recap = str(raw.get("recap") or "").strip()
  if not recap:
    recap = str(raw.get("title") or "")
  return {
    "title": str(raw.get("title") or "暮らしの総括"),
    "recap": recap,
    "mascotId": mascotId,
    "modelUsed": usedModel,
  }
