"""Ruler request detection, crisis heuristics, and JSON merge for specialist calls."""

from __future__ import annotations

import json
import os
import re
from typing import Any


DEFAULT_POLICY: dict[str, Any] = {
  "processBeansRatio": 0.5,
  "investSugarImport": 0.0,
  "reserveReleaseRatio": 0.0,
  "reserveMintingRatio": 0.0,
  "tradeStance": "closed",
  "sugarSubsidy": 0.0,
  "enforcementPriority": 1.0,
  "blackMarketCrackdown": 0.0,
  "foodRationPriority": "equal",
  "distributionBudgetRatio": 0.0,
  "bureaucracyEfficiency": 1.0,
  "hanSatsuIssueRatio": 0.0,
  "goldSilverTargetRatio": 1.0,
}

DEFAULT_LAW_NUMBERS: dict[str, Any] = {
  "targetItem": "zundaNotes",
  "taxRate": 0.1,
  "penalty": "confiscate_partial",
  "enforcementBudget": 20.0,
  "durationTurns": 1,
}

CRISIS_KEYWORDS: tuple[str, ...] = (
  "飢饉",
  "凶作",
  "天明",
  "享保の飢饉",
  "天保",
  "戦争",
  "戦役",
  "黒船",
  "開国",
  "打ちこわし",
  "一揆",
  "米騒動",
  "震災",
  "関東大震災",
  "敗戦",
  "空襲",
  "太平洋戦争",
  "西南戦争",
  "famine",
  "drought",
  "war",
  "bakumatsu",
  "perry",
)

RULER_MODEL_MARKERS: tuple[str, ...] = (
  "qwen3.6-27b",
  "qwen3.6-27b",
  "qwen3-27b",
  "zunda-ruler",
  "ruler",
)

RULER_PROMPT_MARKERS: tuple[str, ...] = (
  "edo/modern japanese ruler agent",
  "ruler agent",
  "output json with law, policy",
)


def envCsv(name: str, fallback: str) -> list[str]:
  raw = os.getenv(name, fallback).strip()
  return [item.strip() for item in raw.split(",") if item.strip()]


def specialistModels() -> dict[str, str]:
  return {
    "policy": os.getenv("GW_POLICY_MODEL", "qwen3-4b-instruct-2507").strip(),
    "ids": os.getenv("GW_IDS_MODEL", "qwen2.5-7b-instruct").strip(),
    "prose": os.getenv("GW_PROSE_MODEL", "qwen2.5-14b-instruct").strip(),
    "crisis": os.getenv("GW_CRISIS_MODEL", "qwen3.6-27b").strip(),
  }


def rulerModelIds() -> list[str]:
  return envCsv("GW_RULER_MODELS", "qwen3.6-27b,qwen3.6-27b,zunda-ruler")


def isRulerModel(model: str) -> bool:
  lowered = (model or "").strip().lower()
  if not lowered:
    return False
  if lowered in {item.lower() for item in rulerModelIds()}:
    return True
  return any(marker in lowered for marker in RULER_MODEL_MARKERS)


def messagesText(messages: list[Any]) -> str:
  parts: list[str] = []
  for item in messages:
    if not isinstance(item, dict):
      continue
    parts.append(str(item.get("content") or ""))
  return "\n".join(parts)


def isRulerRequest(model: str, messages: list[Any]) -> bool:
  if isRulerModel(model):
    return True
  blob = messagesText(messages).lower()
  return any(marker in blob for marker in RULER_PROMPT_MARKERS)


def isCrisisPrompt(text: str) -> bool:
  lowered = (text or "").lower()
  return any(keyword.lower() in lowered for keyword in CRISIS_KEYWORDS)


def crisisUses27b() -> bool:
  return os.getenv("GW_CRISIS_USE_27B", "1").strip().lower() in ("1", "true", "yes", "on")


def pickProseModel(userText: str) -> str:
  models = specialistModels()
  if crisisUses27b() and isCrisisPrompt(userText):
    return models["crisis"]
  return models["prose"]


def repairJsonText(text: str) -> str:
  cleaned = (text or "").strip()
  cleaned = cleaned.replace("\ufeff", "")
  cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"')
  cleaned = cleaned.replace("\u2018", "'").replace("\u2019", "'")
  cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
  cleaned = re.sub(r"\bTrue\b", "true", cleaned)
  cleaned = re.sub(r"\bFalse\b", "false", cleaned)
  cleaned = re.sub(r"\bNone\b", "null", cleaned)
  return cleaned


def extractJsonObject(text: str) -> dict[str, Any]:
  text = repairJsonText(text)
  if text.startswith("```"):
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
  text = text.strip()
  candidates: list[str] = [text]
  braceMatch = re.search(r"\{[\s\S]*\}", text)
  if braceMatch:
    candidates.append(braceMatch.group(0))
  candidates.extend(
    match.group(0)
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
  )
  lastError: Exception | None = None
  seen: set[str] = set()
  for candidate in candidates:
    repaired = repairJsonText(candidate)
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


def userContent(messages: list[Any]) -> str:
  for item in reversed(messages):
    if isinstance(item, dict) and item.get("role") == "user":
      return str(item.get("content") or "")
  return messagesText(messages)


def policyPrompt(userPrompt: str) -> tuple[str, str]:
  systemPrompt = (
    "You fill numeric Edo/Japan policy knobs. "
    "Output one JSON object with keys policy and lawNumbers. "
    "policy uses processBeansRatio, investSugarImport, reserveReleaseRatio, "
    "reserveMintingRatio, tradeStance (closed|limited|open), sugarSubsidy, "
    "enforcementPriority, blackMarketCrackdown, foodRationPriority "
    "(equal|urban|rural|military), distributionBudgetRatio, bureaucracyEfficiency, "
    "hanSatsuIssueRatio, goldSilverTargetRatio. "
    "lawNumbers uses targetItem, taxRate, penalty, enforcementBudget, durationTurns. "
    "No decree text. JSON only."
  )
  return systemPrompt, userPrompt


def idsPrompt(userPrompt: str) -> tuple[str, str]:
  systemPrompt = (
    "Pick at most 3 historicalPolicyIds from the coefficient hand in the prompt. "
    "Empty array is normal. JSON only: {\"historicalPolicyIds\": []}."
  )
  return systemPrompt, userPrompt


def prosePrompt(userPrompt: str) -> tuple[str, str]:
  systemPrompt = (
    "You write the Japanese decree and a short rulerReason. "
    "JSON only: {\"decree\": \"日本語の短い布告\", \"rulerReason\": \"日本語1文\"}. "
    "Make the decree concrete. No other keys."
  )
  return systemPrompt, userPrompt


def _asDict(value: Any) -> dict[str, Any]:
  return value if isinstance(value, dict) else {}


def mergeRulerParts(
  policyPart: dict[str, Any] | None,
  idsPart: dict[str, Any] | None,
  prosePart: dict[str, Any] | None,
) -> dict[str, Any]:
  policyPart = policyPart or {}
  idsPart = idsPart or {}
  prosePart = prosePart or {}
  policyRaw = _asDict(policyPart.get("policy")) or {
    key: policyPart[key] for key in DEFAULT_POLICY if key in policyPart
  }
  policy = dict(DEFAULT_POLICY)
  policy.update({key: policyRaw[key] for key in policy if key in policyRaw})
  lawNumbers = dict(DEFAULT_LAW_NUMBERS)
  numbersRaw = _asDict(policyPart.get("lawNumbers")) or _asDict(policyPart.get("law"))
  lawNumbers.update({key: numbersRaw[key] for key in lawNumbers if key in numbersRaw})
  decree = str(
    prosePart.get("decree")
    or _asDict(prosePart.get("law")).get("decree")
    or ""
  ).strip()
  reason = str(
    prosePart.get("rulerReason")
    or prosePart.get("reason")
    or ""
  ).strip()
  rawIds = idsPart.get("historicalPolicyIds", idsPart.get("activatedPolicyIds", []))
  if isinstance(rawIds, str):
    historicalIds = [rawIds] if rawIds.strip() else []
  elif isinstance(rawIds, list):
    historicalIds = [str(item) for item in rawIds if str(item).strip()][:3]
  else:
    historicalIds = []
  return {
    "law": {
      "decree": decree,
      "targetItem": str(lawNumbers["targetItem"]),
      "taxRate": float(lawNumbers["taxRate"]),
      "penalty": str(lawNumbers["penalty"]),
      "enforcementBudget": float(lawNumbers["enforcementBudget"]),
      "durationTurns": int(lawNumbers["durationTurns"]),
    },
    "policy": policy,
    "historicalPolicyIds": historicalIds,
    "rulerReason": reason,
  }
