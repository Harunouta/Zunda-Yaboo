"""Historical policy catalog: LLM-selectable action means, not timeline-locked shocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.law_and_policy import PolicyPackage

WORKSPACE = Path(__file__).resolve().parents[1]
POLICY_PATH = WORKSPACE / "data" / "events" / "policies" / "catalog.yaml"


@dataclass
class PolicyOption:
  policyId: str
  title: str
  promptForLeader: str
  promptForOpinionLeader: str = ""
  historicalYearMonth: str = ""
  availableFrom: str = "1603-01"
  availableUntil: str = "2026-08"
  targetArea: str = "ALL"
  shock: dict[str, float] = field(default_factory=dict)
  policyTweaks: dict[str, Any] = field(default_factory=dict)
  notes: str = ""


def _yearMonthKey(text: str) -> str:
  parts = str(text).strip().replace("_", "-").split("-")
  if len(parts) < 2:
    return f"{int(parts[0]):04d}-01"
  return f"{int(parts[0]):04d}-{int(parts[1]):02d}"


@lru_cache(maxsize=1)
def loadPolicyCatalog() -> dict[str, PolicyOption]:
  if not POLICY_PATH.exists():
    return {}
  raw = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
  catalog: dict[str, PolicyOption] = {}
  for policyId, entry in raw.items():
    if not isinstance(entry, dict):
      continue
    catalog[str(policyId)] = PolicyOption(
      policyId=str(policyId),
      title=str(entry.get("title") or policyId),
      promptForLeader=str(entry.get("promptForLeader") or ""),
      promptForOpinionLeader=str(entry.get("promptForOpinionLeader") or ""),
      historicalYearMonth=str(entry.get("historicalYearMonth") or ""),
      availableFrom=_yearMonthKey(str(entry.get("availableFrom") or "1603-01")),
      availableUntil=_yearMonthKey(str(entry.get("availableUntil") or "2026-08")),
      targetArea=str(entry.get("targetArea") or "ALL"),
      shock=dict(entry.get("effects") or {}),
      policyTweaks=dict(entry.get("policyTweaks") or {}),
      notes=str(entry.get("notes") or ""),
    )
  return catalog


def reloadPolicies() -> None:
  loadPolicyCatalog.cache_clear()
  try:
    from src.policy_items import reloadPolicyItems

    reloadPolicyItems()
  except ImportError:
    pass


def isAvailable(option: PolicyOption, yearMonth: str) -> bool:
  stamp = _yearMonthKey(yearMonth)
  return option.availableFrom <= stamp <= option.availableUntil


def listAvailablePolicies(yearMonth: str) -> list[PolicyOption]:
  return [item for item in loadPolicyCatalog().values() if isAvailable(item, yearMonth)]


def historicalPoliciesForMonth(yearMonth: str) -> list[PolicyOption]:
  stamp = _yearMonthKey(yearMonth)
  return [
    item
    for item in loadPolicyCatalog().values()
    if item.historicalYearMonth and _yearMonthKey(item.historicalYearMonth) == stamp
  ]


def policyTimingLabel(policyId: str, yearMonth: str) -> str:
  option = loadPolicyCatalog().get(policyId)
  if option is None or not option.historicalYearMonth:
    return "original"
  canonical = _yearMonthKey(option.historicalYearMonth)
  stamp = _yearMonthKey(yearMonth)
  if stamp == canonical:
    return "on_historical_month"
  if stamp < canonical:
    return "earlier_than_history"
  return "later_than_history"


def formatPoliciesForLeader(yearMonth: str, limit: int = 3, hand: list[PolicyOption] | None = None) -> str:
  from src.policy_items import formatItemHand

  text = formatItemHand(hand or [])
  coincidences = historicalPoliciesForMonth(yearMonth)[:limit]
  if coincidences:
    names = ", ".join(f"{item.policyId}({item.title})" for item in coincidences)
    text += (
      f" Trivia: this month is the canonical date of {names}. "
      "Matching it, ignoring it, or doing a similar reform earlier/later is all allowed."
    )
  return text


def applyPolicyTweaks(policy: PolicyPackage, option: PolicyOption) -> PolicyPackage:
  from src.policy_items import blendPolicyTweaks

  return blendPolicyTweaks(policy, option)


def optionToShock(option: PolicyOption) -> dict[str, Any]:
  shock = dict(option.shock)
  shock["targetArea"] = option.targetArea
  return shock
