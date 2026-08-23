"""Persistent opinion-leader roster, abnormal-month SLM calls, and mass panic propagation.

Phase 2: flee / black_market apply tiny economy shocks; organize builds influence.
When founding-mode influence crosses a threshold, catalog regions flip Historical → Simulated
(tax/compliance penalty weighted by taxShare + ongoing legitimacy/food stress).
Regions: edo_core, osaka_hub, tohoku_rim (see REGION_CATALOG).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.events import DISASTER_LEADER_THRESHOLD, getEventPayload, isAbnormalMonth

DEFAULT_OPINION_LEADER_COUNT = int(os.getenv("ZUNDA_OPINION_LEADERS", "5"))
# Historical → Simulated flip (multi-region; edo_core remains the primary tax hub).
FOUNDING_INFLUENCE_THRESHOLD = float(os.getenv("ZUNDA_FOUNDING_THRESHOLD", "0.18"))
SIMULATED_TAX_FACTOR = 0.85
SIMULATED_COMPLIANCE_FACTOR = 0.9
SIMULATED_LEGITIMACY_DRAIN = 0.012
SIMULATED_FOOD_DRAIN_RATE = 0.006
REGION_MODE_HISTORICAL = "historical"
REGION_MODE_SIMULATED = "simulated"

# regionId -> {label, foundingThreshold, taxShare, foodDrainScale}
# taxShare weights how hard a Simulated flip hits national tax; foodDrainScale stacks.
REGION_CATALOG: dict[str, dict[str, Any]] = {
  "edo_core": {
    "label": "江戸核心",
    "foundingThreshold": FOUNDING_INFLUENCE_THRESHOLD,
    "taxShare": 0.55,
    "foodDrainScale": 1.0,
  },
  "osaka_hub": {
    "label": "大坂・畿内",
    "foundingThreshold": FOUNDING_INFLUENCE_THRESHOLD + 0.04,
    "taxShare": 0.25,
    "foodDrainScale": 0.7,
  },
  "tohoku_rim": {
    "label": "東北縁",
    "foundingThreshold": max(0.12, FOUNDING_INFLUENCE_THRESHOLD - 0.04),
    "taxShare": 0.20,
    "foodDrainScale": 0.85,
  },
}
DEFAULT_REGION_ID = "edo_core"
# Founding influence from another region's home counts at this fraction.
HOME_FOUNDING_AWAY_WEIGHT = 0.55

AGENT_HOME_REGION: dict[str, str] = {
  "elder_village": "edo_core",
  "merchant_traveler": "osaka_hub",
  "cult_preacher": "edo_core",
  "smuggler_broker": "osaka_hub",
  "frontier_settler": "tohoku_rim",
}

ORGANIZE_INFLUENCE_DELTA = 0.04
MAX_INFLUENCE = 1.0
PEACE_INFLUENCE_DECAY = 0.92
FOUNDING_INFLUENCE_DECAY = 0.97
INFLUENCE_FLOOR = 0.05
PARALLEL_MAX_WORKERS = 2

# Minimal economy hooks (keep small so dry-runs stay stable).
FLEE_POP_RATE = 0.0008
BLACK_MARKET_FOOD_RATE = 0.012
BLACK_MARKET_SUGAR_RATE = 0.02
POPULATION_FLOOR = 100.0

INTENT_MODE_MAP = {
  "flee": "fleeing",
  "black_market": "black_market",
  "organize": "founding",
  "hoard": "embedded",
  "comply": "embedded",
}

VALID_INTENTS = frozenset(INTENT_MODE_MAP.keys())

DEFAULT_ROSTER_SPEC: tuple[tuple[str, str], ...] = (
  ("elder_village", "村の長老"),
  ("merchant_traveler", "噂好きの行商人"),
  ("cult_preacher", "新興宗教の教祖"),
  ("smuggler_broker", "闇市の仲買"),
  ("frontier_settler", "辺境の開拓百姓"),
)

ROLE_RUMOR_BIAS: dict[str, str] = {
  "elder_village": "蔵の鍵を握る者が口を閉ざした、と村で囁く",
  "merchant_traveler": "隣村の市で砂糖が消えた、と行商が言う",
  "cult_preacher": "豆が腐る呪いは天罰だ、と説く者が増えた",
  "smuggler_broker": "夜市なら高いが手元に残る、と囁かれる",
  "frontier_settler": "この土地を捨てて北へ逃げよう、と畑で噂",
}


def _clamp01(value: float) -> float:
  return max(min(float(value), 1.0), 0.0)


def defaultAgent(agentId: str, role: str) -> dict[str, Any]:
  homeRegionId = AGENT_HOME_REGION.get(agentId, DEFAULT_REGION_ID)
  return {
    "agentId": agentId,
    "role": role,
    "influence": 0.05,
    "wealth": 10.0,
    "regionId": homeRegionId,
    "homeRegionId": homeRegionId,
    "mode": "embedded",
    "lastPanic": 0.0,
    "lastRumor": "",
    "memorySnippet": "",
  }


def createDefaultRoster() -> list[dict[str, Any]]:
  return [defaultAgent(agentId, role) for agentId, role in DEFAULT_ROSTER_SPEC]


def ensureRoster(meta: dict[str, Any] | None) -> list[dict[str, Any]]:
  """Load agents from checkpoint meta or seed the fixed roster."""
  meta = meta if isinstance(meta, dict) else {}
  raw = meta.get("agents")
  if not isinstance(raw, list) or not raw:
    roster = createDefaultRoster()
    meta["agents"] = roster
    return roster

  byId = {str(item.get("agentId")): item for item in raw if isinstance(item, dict)}
  roster: list[dict[str, Any]] = []
  for agentId, role in DEFAULT_ROSTER_SPEC:
    existing = byId.get(agentId)
    if existing is None:
      roster.append(defaultAgent(agentId, role))
      continue
    merged = defaultAgent(agentId, role)
    merged.update({
      "influence": _clamp01(existing.get("influence", merged["influence"])),
      "wealth": float(existing.get("wealth", merged["wealth"])),
      "homeRegionId": AGENT_HOME_REGION.get(agentId, DEFAULT_REGION_ID),
      "regionId": str(existing.get("regionId") or AGENT_HOME_REGION.get(agentId, DEFAULT_REGION_ID)),
      "mode": str(existing.get("mode", "embedded")),
      "lastPanic": _clamp01(existing.get("lastPanic", 0.0)),
      "lastRumor": str(existing.get("lastRumor", "")),
      "memorySnippet": str(existing.get("memorySnippet", "")),
      "role": str(existing.get("role", role)),
    })
    roster.append(merged)
  meta["agents"] = roster
  return roster


def abnormalTriggerLabels(events: list[str], disasterMultiplier: float) -> list[str]:
  labels = list(events)
  if disasterMultiplier < DISASTER_LEADER_THRESHOLD and "climate_disaster" not in labels:
    labels.append("climate_disaster")
  return labels


def buildOpinionPrompt(
  agent: dict[str, Any],
  events: list[str],
  yearMonth: str,
  *,
  foodHint: str,
  legitimacyHint: str,
  decreeSnippet: str,
) -> str:
  """Fragmented context only — do not pass exact national stockpiles."""
  eventBits = [
    getEventPayload(eventId).promptForOpinionLeader
    for eventId in events
    if getEventPayload(eventId)
  ]
  memory = str(agent.get("memorySnippet") or "").strip()
  memoryLine = f" Your recent memory: {memory}." if memory else ""
  context = " / ".join(eventBits) if eventBits else "空気がおかしい。隣村の噂だけが頼りだ。"
  return (
    f"You are {agent['role']} ({agent['agentId']}) in {yearMonth}, "
    f"home={agent.get('homeRegionId')}, region={agent.get('regionId')}. "
    f"mode={agent.get('mode', 'embedded')}. influence={float(agent.get('influence', 0)):.2f}. "
    f"You only know fragments: foodFeel={foodHint}, regimeFeel={legitimacyHint}, "
    f"decreeWhisper={decreeSnippet or '聞こえない'}. "
    f"Context: {context}.{memoryLine} "
    "Output JSON: panic(0-1), rumor (concrete Japanese), "
    "intent (comply|hoard|flee|black_market|organize), localBias (short Japanese bias). "
    "Do NOT claim to know national warehouse totals."
  )


def dryRunOpinionLeader(
  agent: dict[str, Any],
  events: list[str],
  yearMonth: str,
  foodPerCapita: float,
) -> dict[str, Any]:
  panic = 0.25
  if events:
    panic += 0.35
  if foodPerCapita < 0.05:
    panic += 0.25
  elif foodPerCapita < 0.12:
    panic += 0.1
  agentId = str(agent["agentId"])
  panic = _clamp01(panic + (sum(ord(ch) for ch in f"{yearMonth}:{agentId}") % 17) / 100.0)

  rumorBase = ROLE_RUMOR_BIAS.get(agentId, "市に不安な噂が立つ")
  if events:
    rumor = f"{agent['role']}: {rumorBase}／事件={','.join(events[:2])}"
  else:
    rumor = f"{agent['role']}: {rumorBase}"

  if panic >= 0.75:
    intent = "flee"
  elif panic >= 0.6:
    intent = "black_market" if agentId == "smuggler_broker" else "hoard"
  elif agentId in ("cult_preacher", "frontier_settler") and (
    panic >= 0.4 or any("famine" in eventId or "eruption" in eventId for eventId in events)
  ):
    intent = "organize"
  else:
    intent = "hoard" if panic >= 0.35 else "comply"

  return {
    "agentId": agentId,
    "role": agent["role"],
    "panic": panic,
    "rumor": rumor,
    "intent": intent,
    "localBias": f"{agent['role']}視点の断片",
    "mode": agent.get("mode", "embedded"),
    "influence": float(agent.get("influence", 0.05)),
    "source": "dry_run",
  }


def decayRosterInfluence(roster: list[dict[str, Any]]) -> dict[str, float]:
  """Quiet-month fade: founding decays slower than embedded influence."""
  before = [float(agent.get("influence", 0.0)) for agent in roster]
  for agent in roster:
    rate = (
      FOUNDING_INFLUENCE_DECAY
      if str(agent.get("mode")) == "founding"
      else PEACE_INFLUENCE_DECAY
    )
    agent["influence"] = max(INFLUENCE_FLOOR, float(agent.get("influence", 0.0)) * rate)
  after = [float(agent.get("influence", 0.0)) for agent in roster]
  return {
    "meanBefore": round(sum(before) / max(len(before), 1), 4),
    "meanAfter": round(sum(after) / max(len(after), 1), 4),
  }


def applyIntentStub(agent: dict[str, Any], intent: str) -> None:
  """Record mode / tiny influence bumps; economy effects are applied separately."""
  normalized = intent if intent in VALID_INTENTS else "comply"
  newMode = INTENT_MODE_MAP.get(normalized, "embedded")
  if normalized in ("flee", "black_market", "organize"):
    agent["mode"] = newMode
  if normalized == "organize":
    agent["influence"] = _clamp01(float(agent.get("influence", 0.0)) + ORGANIZE_INFLUENCE_DELTA)
  elif normalized == "hoard":
    agent["influence"] = _clamp01(float(agent.get("influence", 0.0)) + 0.002)


def applyOpinionEconomyEffects(
  economy: Any,
  opinionAgents: list[dict[str, Any]],
) -> dict[str, float]:
  """Apply flee / black_market micro shocks from active opinion leaders."""
  fledPopulation = 0.0
  foodDrain = 0.0
  sugarDrain = 0.0

  for item in opinionAgents:
    intent = str(item.get("intent", "comply"))
    influence = _clamp01(float(item.get("influence", 0.05)))
    panic = _clamp01(float(item.get("panic", 0.0)))
    weight = influence * (0.5 + 0.5 * panic)

    if intent == "flee":
      loss = economy.population * FLEE_POP_RATE * weight
      economy.population = max(economy.population - loss, POPULATION_FLOOR)
      fledPopulation += loss
    elif intent == "black_market":
      foodLoss = economy.foodBuffer * BLACK_MARKET_FOOD_RATE * weight
      sugarLoss = economy.sugarStock * BLACK_MARKET_SUGAR_RATE * weight
      economy.foodBuffer = max(economy.foodBuffer - foodLoss, 0.0)
      economy.sugarStock = max(economy.sugarStock - sugarLoss, 0.0)
      foodDrain += foodLoss
      sugarDrain += sugarLoss

  return {
    "fledPopulation": round(fledPopulation, 3),
    "foodDrain": round(foodDrain, 3),
    "sugarDrain": round(sugarDrain, 3),
  }


def ensureRegions(meta: dict[str, Any] | None) -> dict[str, Any]:
  """Persist per-region governance mode on checkpoint meta."""
  meta = meta if isinstance(meta, dict) else {}
  regions = meta.get("regions")
  if not isinstance(regions, dict):
    regions = {}
  for regionId, spec in REGION_CATALOG.items():
    entry = regions.get(regionId)
    if not isinstance(entry, dict):
      entry = {}
    regions[regionId] = {
      "mode": str(entry.get("mode") or REGION_MODE_HISTORICAL),
      "flippedAt": entry.get("flippedAt"),
      "peakFoundingInfluence": float(entry.get("peakFoundingInfluence") or 0.0),
      "label": spec["label"],
      "foundingThreshold": float(spec["foundingThreshold"]),
      "taxShare": float(spec["taxShare"]),
      "foodDrainScale": float(spec["foodDrainScale"]),
    }
  meta["regions"] = regions
  return regions


def buildRegionSnapshot(meta: dict[str, Any] | None) -> dict[str, Any]:
  """Read-only snapshot used for tax penalty / UI before/after founding updates."""
  regions = ensureRegions(meta if isinstance(meta, dict) else {})
  primary = regions[DEFAULT_REGION_ID]
  simulatedShare = sum(
    float(regions[rid].get("taxShare") or 0.0)
    for rid in regions
    if str(regions[rid].get("mode")) == REGION_MODE_SIMULATED
  )
  return {
    "regionId": DEFAULT_REGION_ID,
    "mode": primary.get("mode", REGION_MODE_HISTORICAL),
    "flippedAt": primary.get("flippedAt"),
    "peakFoundingInfluence": round(float(primary.get("peakFoundingInfluence", 0.0)), 4),
    "threshold": FOUNDING_INFLUENCE_THRESHOLD,
    "flippedThisMonth": False,
    "flippedRegionIds": [],
    "simulatedTaxShare": round(simulatedShare, 4),
    "regions": {
      rid: {
        "mode": regions[rid].get("mode"),
        "flippedAt": regions[rid].get("flippedAt"),
        "peakFoundingInfluence": round(float(regions[rid].get("peakFoundingInfluence", 0.0)), 4),
        "label": regions[rid].get("label"),
      }
      for rid in regions
    },
  }


def foundingPeakForRegion(roster: list[dict[str, Any]], regionId: str) -> float:
  """Home organizers count fully; other regions' founders count at away weight."""
  homePeaks: list[float] = []
  awayPeaks: list[float] = []
  for agent in roster:
    if str(agent.get("mode")) != "founding":
      continue
    influence = float(agent.get("influence", 0.0))
    home = str(agent.get("homeRegionId") or agent.get("regionId") or DEFAULT_REGION_ID)
    if home == regionId:
      homePeaks.append(influence)
    else:
      awayPeaks.append(influence)
  peakHome = max(homePeaks) if homePeaks else 0.0
  peakAway = (max(awayPeaks) if awayPeaks else 0.0) * HOME_FOUNDING_AWAY_WEIGHT
  return max(peakHome, peakAway)


def updateRegionFounding(
  meta: dict[str, Any],
  roster: list[dict[str, Any]],
  yearMonth: str,
) -> dict[str, Any]:
  """Flip each catalog region when home-biased founding influence crosses its threshold."""
  regions = ensureRegions(meta)
  flippedIds: list[str] = []
  for regionId, region in regions.items():
    threshold = float(region.get("foundingThreshold") or FOUNDING_INFLUENCE_THRESHOLD)
    peak = foundingPeakForRegion(roster, regionId)
    region["peakFoundingInfluence"] = max(float(region.get("peakFoundingInfluence", 0.0)), peak)
    if str(region.get("mode")) == REGION_MODE_HISTORICAL and peak >= threshold:
      region["mode"] = REGION_MODE_SIMULATED
      region["flippedAt"] = yearMonth
      flippedIds.append(regionId)
    regions[regionId] = region
  meta["regions"] = regions
  snapshot = buildRegionSnapshot(meta)
  snapshot["flippedThisMonth"] = DEFAULT_REGION_ID in flippedIds
  snapshot["flippedRegionIds"] = flippedIds
  return snapshot


def applySimulatedRegionEffects(
  economy: Any,
  governance: Any,
  regionState: dict[str, Any],
  drainLegitimacy: bool = True,
) -> dict[str, float]:
  """Ongoing stress while any region is Simulated; scales with foodDrainScale sum."""
  regionsMeta = regionState.get("regions") if isinstance(regionState.get("regions"), dict) else None
  scales: list[float] = []
  if regionsMeta:
    for rid, entry in regionsMeta.items():
      if str(entry.get("mode")) != REGION_MODE_SIMULATED:
        continue
      spec = REGION_CATALOG.get(str(rid)) or {}
      scales.append(float(spec.get("foodDrainScale") or 1.0))
  elif str(regionState.get("mode")) == REGION_MODE_SIMULATED:
    scales.append(1.0)
  if not scales:
    return {"foodDrain": 0.0, "legitimacyDrain": 0.0, "simulatedRegionCount": 0}
  scaleSum = sum(scales)
  foodDrain = economy.foodBuffer * SIMULATED_FOOD_DRAIN_RATE * scaleSum
  economy.foodBuffer = max(economy.foodBuffer - foodDrain, 0.0)
  legitDrain = 0.0
  if drainLegitimacy:
    before = float(governance.legitimacy)
    governance.legitimacy = max(before - SIMULATED_LEGITIMACY_DRAIN * min(scaleSum, 2.0), 0.05)
    legitDrain = before - float(governance.legitimacy)
  return {
    "foodDrain": round(foodDrain, 3),
    "legitimacyDrain": round(legitDrain, 4),
    "simulatedRegionCount": len(scales),
  }


def applySimulatedTaxPenalty(effective: Any, regionState: dict[str, Any]) -> None:
  """Reduce tax take / compliance from Simulated regions (weighted by taxShare)."""
  share = float(regionState.get("simulatedTaxShare") or 0.0)
  if share <= 0.0 and str(regionState.get("mode")) == REGION_MODE_SIMULATED:
    share = float((REGION_CATALOG.get(DEFAULT_REGION_ID) or {}).get("taxShare") or 1.0)
  if share <= 0.0:
    return
  taxFactor = 1.0 - (1.0 - SIMULATED_TAX_FACTOR) * min(share, 1.0)
  complianceFactor = 1.0 - (1.0 - SIMULATED_COMPLIANCE_FACTOR) * min(share, 1.0)
  effective.effectiveTaxRate = float(effective.effectiveTaxRate) * taxFactor
  effective.complianceRate = float(effective.complianceRate) * complianceFactor
  warnings = list(getattr(effective, "warnings", []) or [])
  if "region_simulated" not in warnings:
    warnings.append("region_simulated")
  effective.warnings = warnings


def _resolveOneLeader(
  agent: dict[str, Any],
  *,
  events: list[str],
  yearMonth: str,
  foodPerCapita: float,
  legitimacy: float,
  decree: str,
  useLlm: bool,
) -> dict[str, Any]:
  foodHint = "腹が減る" if foodPerCapita < 0.08 else ("ギリギリ" if foodPerCapita < 0.15 else "普通に食える噂")
  legitimacyHint = "お上が怪しい" if legitimacy < 0.45 else ("揺れてる" if legitimacy < 0.7 else "まだ信じられてる")
  decreeSnippet = (decree or "")[:40]
  prompt = buildOpinionPrompt(
    agent,
    events,
    yearMonth,
    foodHint=foodHint,
    legitimacyHint=legitimacyHint,
    decreeSnippet=decreeSnippet,
  )

  if not useLlm:
    result = dryRunOpinionLeader(agent, events, yearMonth, foodPerCapita)
  else:
    try:
      from src.llm_client import callOpinionLeader

      raw = callOpinionLeader(prompt, str(agent["agentId"]), str(agent["role"]))
      result = {
        "agentId": agent["agentId"],
        "role": agent["role"],
        "panic": _clamp01(raw.get("panic", 0.3)),
        "rumor": str(raw.get("rumor", "")),
        "intent": str(raw.get("intent", "comply")),
        "localBias": str(raw.get("localBias", "")),
        "mode": agent.get("mode", "embedded"),
        "influence": float(agent.get("influence", 0.05)),
        "source": "llm",
      }
      if result["intent"] not in VALID_INTENTS:
        result["intent"] = "comply"
      if not result["rumor"]:
        fallback = dryRunOpinionLeader(agent, events, yearMonth, foodPerCapita)
        result["rumor"] = fallback["rumor"]
    except Exception as error:
      result = dryRunOpinionLeader(agent, events, yearMonth, foodPerCapita)
      result["source"] = f"llm_fallback:{error}"

  applyIntentStub(agent, str(result["intent"]))
  agent["lastPanic"] = float(result["panic"])
  agent["lastRumor"] = str(result["rumor"])
  agent["memorySnippet"] = str(result["rumor"])[:80]
  result["mode"] = agent.get("mode", "embedded")
  result["influence"] = float(agent.get("influence", 0.05))
  result["prompt"] = prompt
  return result


def resolveOpinionLeaders(
  roster: list[dict[str, Any]],
  *,
  events: list[str],
  disasterMultiplier: float,
  yearMonth: str,
  foodPerCapita: float,
  legitimacy: float,
  decree: str,
  useLlm: bool,
  leaderCount: int,
  parallel: bool = False,
) -> dict[str, Any]:
  """Call up to leaderCount agents on abnormal months; otherwise inactive."""
  if leaderCount <= 0 or not isAbnormalMonth(events, disasterMultiplier):
    return {
      "active": False,
      "trigger": [],
      "agents": [],
    }

  selected = roster[: max(min(leaderCount, len(roster)), 0)]
  trigger = abnormalTriggerLabels(events, disasterMultiplier)
  opinions: list[dict[str, Any]] = []

  if parallel and len(selected) > 1:
    with ThreadPoolExecutor(max_workers=PARALLEL_MAX_WORKERS) as pool:
      futures = {
        pool.submit(
          _resolveOneLeader,
          agent,
          events=events,
          yearMonth=yearMonth,
          foodPerCapita=foodPerCapita,
          legitimacy=legitimacy,
          decree=decree,
          useLlm=useLlm,
        ): agent
        for agent in selected
      }
      for future in as_completed(futures):
        opinions.append(future.result())
    order = {agent["agentId"]: index for index, agent in enumerate(selected)}
    opinions.sort(key=lambda item: order.get(item["agentId"], 999))
  else:
    for agent in selected:
      opinions.append(
        _resolveOneLeader(
          agent,
          events=events,
          yearMonth=yearMonth,
          foodPerCapita=foodPerCapita,
          legitimacy=legitimacy,
          decree=decree,
          useLlm=useLlm,
        )
      )

  return {
    "active": True,
    "trigger": trigger,
    "agents": [
      {
        "agentId": item["agentId"],
        "role": item["role"],
        "panic": round(float(item["panic"]), 3),
        "rumor": item["rumor"],
        "intent": item["intent"],
        "localBias": item.get("localBias", ""),
        "mode": item.get("mode", "embedded"),
        "influence": round(float(item.get("influence", 0.0)), 4),
        "source": item.get("source", ""),
      }
      for item in opinions
    ],
  }


def propagateCrowdFromOpinions(
  opinions: list[dict[str, Any]],
  foodPerCapita: float,
  legitimacy: float,
) -> dict[str, Any]:
  """Numeric mass crowd from leader panic / rumor (no extra LLM)."""
  if not opinions:
    return {
      "rumor": "",
      "anger": 0.15,
      "hoarding": 0.1,
      "riotRisk": 0.05,
      "moodText": "指導者の声が届かない月",
      "crowdMoodDetail": "opinionLeaders empty",
      "eventReaction": "",
      "source": "opinion_propagate_empty",
      "avgPanic": 0.0,
      "maxPanic": 0.0,
    }

  panics = [float(item.get("panic", 0.0)) for item in opinions]
  avgPanic = sum(panics) / len(panics)
  maxPanic = max(panics)
  ranked = sorted(opinions, key=lambda item: float(item.get("panic", 0.0)), reverse=True)
  primary = str(ranked[0].get("rumor", ""))
  secondary = str(ranked[1].get("rumor", "")) if len(ranked) > 1 else ""
  rumorConsensus = primary if not secondary else f"{primary}／また{secondary}"

  baseAnger = 0.1
  if foodPerCapita < 0.05:
    baseAnger += 0.15
  elif foodPerCapita < 0.12:
    baseAnger += 0.05

  anger = _clamp01(baseAnger + 0.6 * avgPanic + 0.2 * maxPanic)
  hoarding = _clamp01(0.15 + avgPanic * 0.7)
  riotRisk = _clamp01(avgPanic * 0.5 + (1.0 - legitimacy) * 0.2)

  topIntent = str(ranked[0].get("intent", "comply"))
  moodText = f"指導者の恐慌が市に伝染する（avgPanic={avgPanic:.2f}）"
  eventReaction = f"主噂={primary[:48]} intent={topIntent}"

  return {
    "rumor": rumorConsensus,
    "anger": anger,
    "hoarding": hoarding,
    "riotRisk": riotRisk,
    "moodText": moodText,
    "crowdMoodDetail": (
      f"propagated from {len(opinions)} leaders; "
      f"avgPanic={avgPanic:.3f} maxPanic={maxPanic:.3f}"
    ),
    "eventReaction": eventReaction,
    "source": "opinion_propagate",
    "avgPanic": round(avgPanic, 3),
    "maxPanic": round(maxPanic, 3),
  }


def attachMascotToCrowd(
  crowd: dict[str, Any],
  *,
  standard: str,
  yearMonth: str,
  foodPerCapita: float,
  legitimacy: float,
  events: list[str],
  decree: str,
  useLlm: bool,
  policySummary: str = "",
  prices: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """One mascot speech pass after mass mood is known (abnormal-month path)."""
  from src.mascot import buildMascotUserPrompt, dryRunMascotSpeech, emptyMascotFields, mascotForStandard

  mascotId = mascotForStandard(standard)
  if mascotId is None:
    crowd.update(emptyMascotFields())
    return crowd

  crowd["mascotId"] = mascotId
  if not useLlm:
    crowd["mascotSpeech"] = dryRunMascotSpeech(
      mascotId,
      yearMonth,
      foodPerCapita,
      bool(events),
      legitimacy=legitimacy,
      events=events,
      decree=decree,
    )
    return crowd

  try:
    from src.llm_client import callCrowd

    prompt = buildMascotUserPrompt(
      yearMonth,
      events,
      foodPerCapita,
      legitimacy,
      decree,
      prices=prices,
      policySummary=policySummary,
    )
    # Reuse crowd call but keep propagated numeric mood; only take speech.
    mood = callCrowd(prompt, mascotId=mascotId)
    crowd["mascotSpeech"] = str(mood.get("mascotSpeech") or mood.get("moodText") or "")
    if mood.get("source"):
      crowd["mascotSource"] = mood.get("source", "llm")
  except Exception as error:
    crowd["mascotSpeech"] = dryRunMascotSpeech(
      mascotId,
      yearMonth,
      foodPerCapita,
      bool(events),
      legitimacy=legitimacy,
      events=events,
      decree=decree,
    )
    crowd["mascotSource"] = f"llm_fallback:{error}"
  return crowd
