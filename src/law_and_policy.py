"""Law (法令) and Policy (政策) — two-tier governance."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PenaltyType(str, Enum):
  FINE = "fine"
  CONFISCATE_PARTIAL = "confiscate_partial"
  CONFISCATE_ALL = "confiscate_all"
  EXILE = "exile"


class TargetItem(str, Enum):
  RAW_BEANS = "rawBeans"
  ZUNDA = "zunda"
  ZUNDA_NOTES = "zundaNotes"
  ANKO = "anko"
  ANKO_NOTES = "ankoNotes"
  AZUKI = "azuki"
  AZUKI_NOTES = "azukiNotes"
  FOOD = "food"
  RICE = "rice"
  GOLD = "gold"
  SILVER = "silver"
  HAN_SATSU = "hanSatsu"
  DOLLAR_NOTES = "dollarNotes"


@dataclass
class LawAct:
  decree: str = ""
  targetItem: str = "zundaNotes"
  taxRate: float = 0.1
  penalty: str = PenaltyType.CONFISCATE_PARTIAL.value
  enforcementBudget: float = 20.0
  lawId: str = ""
  durationTurns: int = 1

  def toDict(self) -> dict[str, Any]:
    return {
      "decree": self.decree,
      "targetItem": self.targetItem,
      "taxRate": self.taxRate,
      "penalty": self.penalty,
      "enforcementBudget": self.enforcementBudget,
      "lawId": self.lawId,
      "durationTurns": self.durationTurns,
    }


@dataclass
class PolicyPackage:
  processBeansRatio: float = 0.5
  investSugarImport: float = 0.0
  reserveReleaseRatio: float = 0.0
  reserveMintingRatio: float = 0.0
  tradeStance: str = "closed"
  sugarSubsidy: float = 0.0
  enforcementPriority: float = 1.0
  blackMarketCrackdown: float = 0.0
  foodRationPriority: str = "equal"
  distributionBudgetRatio: float = 0.0
  bureaucracyEfficiency: float = 1.0
  hanSatsuIssueRatio: float = 0.0
  goldSilverTargetRatio: float = 1.0

  def toDict(self) -> dict[str, Any]:
    return {
      "processBeansRatio": self.processBeansRatio,
      "investSugarImport": self.investSugarImport,
      "reserveReleaseRatio": self.reserveReleaseRatio,
      "reserveMintingRatio": self.reserveMintingRatio,
      "tradeStance": self.tradeStance,
      "sugarSubsidy": self.sugarSubsidy,
      "enforcementPriority": self.enforcementPriority,
      "blackMarketCrackdown": self.blackMarketCrackdown,
      "foodRationPriority": self.foodRationPriority,
      "distributionBudgetRatio": self.distributionBudgetRatio,
      "bureaucracyEfficiency": self.bureaucracyEfficiency,
      "hanSatsuIssueRatio": self.hanSatsuIssueRatio,
      "goldSilverTargetRatio": self.goldSilverTargetRatio,
    }


@dataclass
class RulerDecision:
  law: LawAct = field(default_factory=LawAct)
  policy: PolicyPackage = field(default_factory=PolicyPackage)
  activatedPolicyIds: list[str] = field(default_factory=list)

  def toDict(self) -> dict[str, Any]:
    return {
      "law": self.law.toDict(),
      "policy": self.policy.toDict(),
      "activatedPolicyIds": list(self.activatedPolicyIds),
    }


POLICY_BOUNDS: dict[str, tuple[float, float]] = {
  "processBeansRatio": (0.0, 1.0),
  "investSugarImport": (0.0, 500.0),
  "reserveReleaseRatio": (0.0, 0.5),
  "reserveMintingRatio": (0.0, 0.3),
  "sugarSubsidy": (0.0, 1.0),
  "enforcementPriority": (0.5, 2.0),
  "blackMarketCrackdown": (0.0, 1.0),
  "distributionBudgetRatio": (0.0, 0.5),
  "bureaucracyEfficiency": (0.3, 1.5),
  "hanSatsuIssueRatio": (0.0, 0.4),
  "goldSilverTargetRatio": (0.5, 2.0),
}

VALID_PENALTIES = {item.value for item in PenaltyType}
VALID_TARGET_ITEMS = {item.value for item in TargetItem}


def clipPolicyPackage(policy: PolicyPackage) -> tuple[PolicyPackage, list[str]]:
  clipped: list[str] = []
  for fieldName, (low, high) in POLICY_BOUNDS.items():
    value = getattr(policy, fieldName)
    if value < low:
      setattr(policy, fieldName, low)
      clipped.append(f"policy.{fieldName} floored at {low}")
    elif value > high:
      setattr(policy, fieldName, high)
      clipped.append(f"policy.{fieldName} capped at {high}")
  if policy.tradeStance not in ("closed", "limited", "open"):
    policy.tradeStance = "closed"
    clipped.append("policy.tradeStance reset to closed")
  if policy.foodRationPriority not in ("equal", "urban", "rural", "military"):
    policy.foodRationPriority = "equal"
    clipped.append("policy.foodRationPriority reset to equal")
  return policy, clipped


def clipLawAct(law: LawAct, maxTax: float) -> tuple[LawAct, list[str]]:
  clipped: list[str] = []
  if law.taxRate > maxTax:
    law.taxRate = maxTax
    clipped.append(f"law.taxRate capped at {maxTax}")
  if law.taxRate < 0:
    law.taxRate = 0.0
    clipped.append("law.taxRate floored at 0")
  if law.enforcementBudget < 0:
    law.enforcementBudget = 0.0
  if law.penalty not in VALID_PENALTIES:
    law.penalty = PenaltyType.CONFISCATE_PARTIAL.value
    clipped.append("law.penalty reset to confiscate_partial")
  if law.targetItem not in VALID_TARGET_ITEMS:
    law.targetItem = TargetItem.ZUNDA_NOTES.value
    clipped.append("law.targetItem reset to zundaNotes")
  if law.durationTurns < 1:
    law.durationTurns = 1
  return law, clipped


def parseRulerDecision(raw: dict[str, Any] | list[Any]) -> RulerDecision:
  if isinstance(raw, list):
    raw = next((item for item in raw if isinstance(item, dict)), {})
  if not isinstance(raw, dict):
    raw = {}
  lawRaw = raw.get("law", raw)
  if isinstance(lawRaw, list):
    lawRaw = next((item for item in lawRaw if isinstance(item, dict)), {})
  policyRaw = raw.get("policy", {})
  if isinstance(policyRaw, list):
    policyRaw = next((item for item in policyRaw if isinstance(item, dict)), {})
  if not isinstance(lawRaw, dict):
    lawRaw = {}
  if not isinstance(policyRaw, dict):
    policyRaw = {}
  law = LawAct(
    decree=str(lawRaw.get("decree", lawRaw.get("decreeText", ""))),
    targetItem=str(lawRaw.get("targetItem", lawRaw.get("target_item", "zundaNotes"))),
    taxRate=float(lawRaw.get("taxRate", lawRaw.get("tax_rate", 0.1))),
    penalty=str(lawRaw.get("penalty", PenaltyType.CONFISCATE_PARTIAL.value)),
    enforcementBudget=float(lawRaw.get("enforcementBudget", lawRaw.get("enforcement_budget", 20))),
    lawId=str(lawRaw.get("lawId", lawRaw.get("law_id", ""))),
    durationTurns=int(lawRaw.get("durationTurns", lawRaw.get("duration_turns", 1))),
  )
  policy = PolicyPackage(
    processBeansRatio=float(policyRaw.get("processBeansRatio", 0.5)),
    investSugarImport=float(policyRaw.get("investSugarImport", 0.0)),
    reserveReleaseRatio=float(policyRaw.get("reserveReleaseRatio", 0.0)),
    reserveMintingRatio=float(policyRaw.get("reserveMintingRatio", 0.0)),
    tradeStance=str(policyRaw.get("tradeStance", "closed")),
    sugarSubsidy=float(policyRaw.get("sugarSubsidy", 0.0)),
    enforcementPriority=float(policyRaw.get("enforcementPriority", 1.0)),
    blackMarketCrackdown=float(policyRaw.get("blackMarketCrackdown", 0.0)),
    foodRationPriority=str(policyRaw.get("foodRationPriority", "equal")),
    distributionBudgetRatio=float(policyRaw.get("distributionBudgetRatio", 0.0)),
    bureaucracyEfficiency=float(policyRaw.get("bureaucracyEfficiency", 1.0)),
    hanSatsuIssueRatio=float(policyRaw.get("hanSatsuIssueRatio", 0.0)),
    goldSilverTargetRatio=float(policyRaw.get("goldSilverTargetRatio", 1.0)),
  )
  rawIds = raw.get("historicalPolicyIds", raw.get("activatedPolicyIds", []))
  if isinstance(rawIds, str):
    activated = [rawIds]
  elif isinstance(rawIds, list):
    activated = [str(item) for item in rawIds if str(item).strip()]
  else:
    activated = []
  return RulerDecision(law=law, policy=policy, activatedPolicyIds=activated)
