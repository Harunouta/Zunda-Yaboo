"""Statutes as coefficient items: a small monthly hand that twists mediators/policy.

Picking an id is optional. Effects stack into a decaying coeffKit so the ruler can
nudge growth vs inflation without dumping 3000 laws onto the timeline.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

from src.law_and_policy import PolicyPackage
from src.policies import PolicyOption, isAvailable, loadPolicyCatalog

KIT_INFLATE_BRAKE = "inflateBrake"
KIT_GROWTH = "growth"
KIT_AGRI = "agri"
KIT_LOGISTICS = "logistics"
KIT_ORDER = "order"
KIT_NEUTRAL = "neutral"
KIT_IDS = (
  KIT_INFLATE_BRAKE,
  KIT_GROWTH,
  KIT_AGRI,
  KIT_LOGISTICS,
  KIT_ORDER,
  KIT_NEUTRAL,
)

HAND_SIZE = 8
MAX_ACTIVATE = 3
TWEAK_BLEND = 0.4
KIT_DECAY = 0.88
KIT_CLAMP = 0.25

INFLATE_MARKERS = ("税", "租税", "通貨", "銀行", "日本銀行", "紙幣", "金利", "制限", "倹約", "reform", "ドッジ")
GROWTH_MARKERS = ("工場", "産業", "所得", "投資", "製鐵", "鉄道", "開港", "通商")
AGRI_MARKERS = ("農", "米", "食糧", "配給", "救", "囲米", "土地", "田")
LOGISTICS_MARKERS = ("鉄道", "道路", "港", "登記", "郵便", "運河", "参勤", "交通")
ORDER_MARKERS = ("罰", "刑", "治罪", "警察", "爆発", "保安", "軍")

KIT_DELTAS: dict[str, dict[str, float]] = {
  KIT_INFLATE_BRAKE: {
    "mintBrake": 0.08,
    "trustRepair": 0.05,
    "priceDamp": 0.06,
    "harvestBoost": -0.01,
  },
  KIT_GROWTH: {
    "harvestBoost": 0.03,
    "transferBoost": 0.04,
    "mintBrake": -0.03,
    "spoilCut": 0.01,
  },
  KIT_AGRI: {
    "harvestBoost": 0.07,
    "spoilCut": 0.05,
    "transferBoost": 0.02,
  },
  KIT_LOGISTICS: {
    "transferBoost": 0.09,
    "spoilCut": 0.03,
    "harvestBoost": 0.01,
  },
  KIT_ORDER: {
    "priceDamp": 0.03,
    "trustRepair": 0.02,
    "transferBoost": -0.01,
  },
  KIT_NEUTRAL: {
    "trustRepair": 0.01,
  },
}

KIT_SHOCKS: dict[str, dict[str, float]] = {
  KIT_INFLATE_BRAKE: {"fiatTrustShock": -0.04, "govDemand": 0.02, "socialUnrest": 0.02},
  KIT_GROWTH: {"govDemand": 0.03, "laborDrain": 0.01},
  KIT_AGRI: {"landPollution": -0.04, "stockSpoilage": 0.0},
  KIT_LOGISTICS: {"infraDamage": -0.05},
  KIT_ORDER: {"socialUnrest": -0.05, "laborDrain": 0.01},
  KIT_NEUTRAL: {"govDemand": 0.01},
}


def emptyCoeffKit() -> dict[str, float]:
  return {
    "harvestBoost": 0.0,
    "transferBoost": 0.0,
    "mintBrake": 0.0,
    "trustRepair": 0.0,
    "priceDamp": 0.0,
    "spoilCut": 0.0,
  }


def classifyKit(option: PolicyOption) -> str:
  blob = f"{option.policyId} {option.title} {option.notes}"
  if any(marker in blob for marker in INFLATE_MARKERS):
    return KIT_INFLATE_BRAKE
  if any(marker in blob for marker in LOGISTICS_MARKERS):
    return KIT_LOGISTICS
  if any(marker in blob for marker in AGRI_MARKERS):
    return KIT_AGRI
  if any(marker in blob for marker in ORDER_MARKERS):
    return KIT_ORDER
  if any(marker in blob for marker in GROWTH_MARKERS):
    return KIT_GROWTH
  tweaks = option.policyTweaks
  if str(tweaks.get("tradeStance") or "") == "open":
    return KIT_GROWTH
  if float(tweaks.get("blackMarketCrackdown") or 0.0) >= 0.2:
    return KIT_ORDER
  if float(tweaks.get("reserveReleaseRatio") or 0.0) > 0.0:
    return KIT_AGRI
  return KIT_NEUTRAL


@lru_cache(maxsize=1)
def kitPools() -> dict[str, tuple[PolicyOption, ...]]:
  pools: dict[str, list[PolicyOption]] = {kitId: [] for kitId in KIT_IDS}
  for option in loadPolicyCatalog().values():
    pools[classifyKit(option)].append(option)
  return {kitId: tuple(items) for kitId, items in pools.items()}


def reloadPolicyItems() -> None:
  kitPools.cache_clear()
  try:
    from src.agri_catalog import reloadAgriCatalog

    reloadAgriCatalog()
  except ImportError:
    pass


def _monthSeed(yearMonth: str) -> int:
  digest = hashlib.md5(yearMonth.encode("utf-8")).hexdigest()[:8]
  return int(digest, 16)


def inferNeed(mediatorState: dict[str, Any] | None) -> str:
  if not mediatorState:
    return KIT_AGRI
  national = mediatorState.get("national") or {}
  trust = float(national.get("fiatTrust") or 1.0)
  unrest = float(national.get("socialUnrest") or 0.0)
  labor = float(national.get("laborDrain") or 0.0)
  if trust < 0.85:
    return KIT_INFLATE_BRAKE
  if unrest > 0.12:
    return KIT_ORDER
  if labor > 0.08:
    return KIT_GROWTH
  areas = mediatorState.get("areas") or {}
  pollution = max((float((areas.get(areaId) or {}).get("landPollution") or 0.0) for areaId in areas), default=0.0)
  infra = max((float((areas.get(areaId) or {}).get("infraDamage") or 0.0) for areaId in areas), default=0.0)
  if pollution > 0.15:
    return KIT_AGRI
  if infra > 0.15:
    return KIT_LOGISTICS
  return KIT_GROWTH


def _pickFromPool(
  pool: tuple[PolicyOption, ...],
  yearMonth: str,
  salt: int,
  used: set[str],
) -> PolicyOption | None:
  available = [
    option
    for option in pool
    if option.policyId not in used and isAvailable(option, yearMonth)
  ]
  if not available:
    return None
  index = (_monthSeed(yearMonth) + salt) % len(available)
  return available[index]


def dealPolicyHand(
  yearMonth: str,
  mediatorState: dict[str, Any] | None = None,
  limit: int = HAND_SIZE,
) -> list[PolicyOption]:
  from src.policies import historicalPoliciesForMonth

  used: set[str] = set()
  hand: list[PolicyOption] = []
  for option in historicalPoliciesForMonth(yearMonth)[:3]:
    if option.policyId in used:
      continue
    hand.append(option)
    used.add(option.policyId)
  need = inferNeed(mediatorState)
  pools = kitPools()
  kitOrder = (need,) + tuple(kitId for kitId in KIT_IDS if kitId != need)
  salt = 1
  for kitId in kitOrder:
    while len(hand) < limit:
      picked = _pickFromPool(pools.get(kitId, ()), yearMonth, salt, used)
      salt += 1
      if picked is None:
        break
      hand.append(picked)
      used.add(picked.policyId)
      break
    if len(hand) >= limit:
      break
  return hand[:limit]


def clampActivatedIds(
  rawIds: list[str],
  hand: list[PolicyOption],
  catalog: dict[str, PolicyOption],
) -> list[str]:
  handIds = {item.policyId for item in hand}
  out: list[str] = []
  for policyId in rawIds:
    if policyId in out:
      continue
    if policyId not in catalog:
      continue
    if policyId not in handIds and policyId.startswith("statute_"):
      continue
    out.append(policyId)
    if len(out) >= MAX_ACTIVATE:
      break
  return out


def decayCoeffKit(kit: dict[str, float]) -> None:
  for key in list(kit.keys()):
    kit[key] = max(-KIT_CLAMP, min(KIT_CLAMP, float(kit[key]) * KIT_DECAY))
    if abs(kit[key]) < 0.001:
      kit[key] = 0.0


def kitDeltaMap(kitId: str) -> dict[str, float]:
  try:
    from src.agri_catalog import loadKitClasses

    loaded = loadKitClasses().get(kitId)
    if loaded:
      return loaded
  except Exception:
    pass
  return dict(KIT_DELTAS.get(kitId) or {})


def applyItemToKit(kit: dict[str, float], kitId: str) -> None:
  for key, delta in kitDeltaMap(kitId).items():
    kit[key] = max(-KIT_CLAMP, min(KIT_CLAMP, float(kit.get(key) or 0.0) + delta))


def itemShock(kitId: str, option: PolicyOption) -> dict[str, Any]:
  shock = dict(KIT_SHOCKS.get(kitId) or {})
  if not option.policyId.startswith("statute_"):
    for key, value in option.shock.items():
      if key == "targetArea":
        continue
      shock[key] = float(shock.get(key) or 0.0) + float(value or 0.0)
  shock["targetArea"] = option.targetArea or "ALL"
  return shock


def blendPolicyTweaks(policy: PolicyPackage, option: PolicyOption) -> PolicyPackage:
  for key, value in option.policyTweaks.items():
    if not hasattr(policy, key):
      continue
    current = getattr(policy, key)
    if isinstance(current, (int, float)) and isinstance(value, (int, float)):
      blended = float(current) + (float(value) - float(current)) * TWEAK_BLEND
      setattr(policy, key, type(current)(blended) if isinstance(current, int) else blended)
    else:
      setattr(policy, key, value)
  return policy


def applyMintBrake(policy: PolicyPackage, kit: dict[str, float]) -> PolicyPackage:
  brake = float(kit.get("mintBrake") or 0.0)
  policy.reserveMintingRatio = max(0.0, float(policy.reserveMintingRatio) * (1.0 - brake))
  return policy


def formatItemHand(hand: list[PolicyOption]) -> str:
  if not hand:
    return (
      "Coefficient items: none this month. Invent law freely. "
      "historicalPolicyIds optional, max 3, empty is normal."
    )
  parts = []
  for option in hand:
    kitId = classifyKit(option)
    parts.append(f"{option.policyId}[{kitId}:{option.title}]")
  joined = "; ".join(parts)
  return (
    "Coefficient items (optional, max 3): picking one twists mediators/policy "
    f"toward growth or inflation-brake for several months. Hand: {joined}. "
    "Empty historicalPolicyIds is normal. You may still invent original decrees."
  )
