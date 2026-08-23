"""Agriculture and logistics agents: CSV personas + monthly LLM (crowd model).

Dry-run keeps validate-baseline fast. With --llm, every area×role is called
(parallel workers) and intents scale harvest, rice routes, spoilage, mill, leak.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.agri_catalog import cropLabor, loadAgriRoles, routeMapsForMonth
from src.mediators import AREA_IDS

INTENT_FLOOR = 0.35
INTENT_CEILING = 1.45
FARMER_POLLUTION_WEIGHT = 0.55
FARMER_LABOR_WEIGHT = 0.35
MERCHANT_INFRA_WEIGHT = 0.45
MERCHANT_UNREST_WEIGHT = 0.15
WAREHOUSE_UNREST_WEIGHT = 0.12
MILLER_LABOR_WEIGHT = 0.25
LEAK_SCALE = 0.06
MILLER_BLEND = 0.08
AGRI_MAX_WORKERS = max(int(os.getenv("ZUNDA_AGRI_WORKERS", "3")), 1)
MEMORY_KEEP = 160


def _clipIntent(value: float) -> float:
  return max(INTENT_FLOOR, min(INTENT_CEILING, value))


def _clamp01(value: float) -> float:
  return max(0.0, min(1.0, float(value)))


def defaultAgriAgent(row: dict[str, str]) -> dict[str, Any]:
  return {
    "agentId": f"{row['areaId']}_{row['roleId']}",
    "areaId": row["areaId"],
    "roleId": row["roleId"],
    "displayName": row["displayName"],
    "systemBias": row["systemBias"],
    "lastRumor": "",
    "lastStance": "fair",
    "fatigue": 0.0,
  }


def ensureAgriRoster(meta: dict[str, Any]) -> list[dict[str, Any]]:
  spec = loadAgriRoles()
  raw = meta.get("agriRoster")
  byId: dict[str, dict[str, Any]] = {}
  if isinstance(raw, list):
    for item in raw:
      if isinstance(item, dict) and item.get("agentId"):
        byId[str(item["agentId"])] = item
  roster: list[dict[str, Any]] = []
  for row in spec:
    seed = defaultAgriAgent(row)
    existing = byId.get(seed["agentId"])
    if existing:
      seed["lastRumor"] = str(existing.get("lastRumor") or "")[:MEMORY_KEEP]
      seed["lastStance"] = str(existing.get("lastStance") or "fair")
      seed["fatigue"] = _clamp01(existing.get("fatigue") or 0.0)
    roster.append(seed)
  meta["agriRoster"] = roster
  return roster


def dryRunRoleIntent(
  agent: dict[str, Any],
  mediatorState: dict[str, Any],
  coeffKit: dict[str, float],
  yearMonth: str,
) -> dict[str, Any]:
  national = mediatorState.get("national") or {}
  area = (mediatorState.get("areas") or {}).get(agent["areaId"]) or {}
  pollution = float(area.get("landPollution") or 0.0)
  infra = float(area.get("infraDamage") or 0.0)
  labor = float(national.get("laborDrain") or 0.0)
  unrest = float(national.get("socialUnrest") or 0.0)
  harvestBoost = float(coeffKit.get("harvestBoost") or 0.0)
  transferBoost = float(coeffKit.get("transferBoost") or 0.0)
  spoilCut = float(coeffKit.get("spoilCut") or 0.0)
  calendar = cropLabor(agent["areaId"], yearMonth)
  fatigue = float(agent.get("fatigue") or 0.0)
  roleId = agent["roleId"]
  if roleId == "farmer":
    effort = (
      1.0
      - pollution * FARMER_POLLUTION_WEIGHT
      - labor * FARMER_LABOR_WEIGHT
      + harvestBoost
    ) * calendar
    leak = unrest * 0.05
    stance = "hoard_seed" if pollution > 0.25 else "plant_hard"
  elif roleId == "merchant":
    effort = 1.0 - infra * MERCHANT_INFRA_WEIGHT + unrest * MERCHANT_UNREST_WEIGHT + transferBoost
    leak = unrest * 0.08
    stance = "wait_road" if infra > 0.25 else "ship_hard"
  elif roleId == "warehouse":
    effort = 1.0 + spoilCut - unrest * WAREHOUSE_UNREST_WEIGHT
    leak = unrest * 0.04
    stance = "lock_kura" if unrest > 0.2 else "fair"
  else:
    effort = 1.0 - labor * MILLER_LABOR_WEIGHT + harvestBoost * 0.5
    leak = 0.02
    stance = "night_mill" if harvestBoost > 0 else "fair"
  effort = _clipIntent(effort * (1.0 - fatigue * 0.15))
  rumor = f"{agent['displayName']}は{stance}で動く（{yearMonth}）"
  return {
    "agentId": agent["agentId"],
    "areaId": agent["areaId"],
    "roleId": roleId,
    "effort": effort,
    "blackMarketLeak": _clamp01(leak),
    "stance": stance,
    "rumor": rumor,
    "source": "dry_run",
  }


def buildAgriPrompt(
  agent: dict[str, Any],
  mediatorState: dict[str, Any],
  coeffKit: dict[str, float],
  yearMonth: str,
  events: list[str],
  decree: str,
) -> str:
  area = (mediatorState.get("areas") or {}).get(agent["areaId"]) or {}
  national = mediatorState.get("national") or {}
  memory = str(agent.get("lastRumor") or "").strip()
  memoryLine = f" Recent memory: {memory}." if memory else ""
  eventBit = ",".join(events[:4]) if events else "静かな月"
  return (
    f"You are {agent['displayName']} ({agent['roleId']}) in {agent['areaId']}, {yearMonth}. "
    f"Bias: {agent['systemBias']}. "
    f"You feel landPollution={float(area.get('landPollution') or 0):.2f}, "
    f"infraDamage={float(area.get('infraDamage') or 0):.2f}, "
    f"unrest={float(national.get('socialUnrest') or 0):.2f}, "
    f"laborDrain={float(national.get('laborDrain') or 0):.2f}, "
    f"fiatTrust={float(national.get('fiatTrust') or 1):.2f}, "
    f"kitHarvest={float(coeffKit.get('harvestBoost') or 0):.2f}, "
    f"kitShip={float(coeffKit.get('transferBoost') or 0):.2f}. "
    f"decreeWhisper={decree or 'なし'}. events={eventBit}.{memoryLine} "
    "Output JSON: effort (0.35-1.45 how hard you work this month), "
    "blackMarketLeak (0-1 how much you siphon to the night market), "
    "stance (short english tag), rumor (one vivid Japanese sentence). "
    "Do not invent national warehouse totals."
  )


def _parseAgriLlm(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
  merged = dict(fallback)
  merged["effort"] = _clipIntent(float(raw.get("effort", fallback["effort"])))
  merged["blackMarketLeak"] = _clamp01(raw.get("blackMarketLeak", fallback["blackMarketLeak"]))
  merged["stance"] = str(raw.get("stance") or fallback["stance"])[:40]
  rumor = str(raw.get("rumor") or fallback["rumor"]).strip()
  if rumor:
    merged["rumor"] = rumor[:180]
  merged["source"] = "llm"
  return merged


def _resolveOneAgri(
  agent: dict[str, Any],
  mediatorState: dict[str, Any],
  coeffKit: dict[str, float],
  yearMonth: str,
  events: list[str],
  decree: str,
  useLlm: bool,
) -> dict[str, Any]:
  fallback = dryRunRoleIntent(agent, mediatorState, coeffKit, yearMonth)
  if not useLlm:
    return fallback
  try:
    from src.llm_client import callAgriAgent

    prompt = buildAgriPrompt(agent, mediatorState, coeffKit, yearMonth, events, decree)
    raw = callAgriAgent(prompt, agent["displayName"], agent["roleId"])
    return _parseAgriLlm(raw, fallback)
  except Exception as error:
    fallback["source"] = f"llm_fallback:{error}"
    return fallback


def resolveAgriLogistics(
  roster: list[dict[str, Any]],
  mediatorState: dict[str, Any],
  coeffKit: dict[str, float],
  yearMonth: str,
  events: list[str],
  decree: str,
  useLlm: bool,
  parallel: bool = True,
) -> dict[str, Any]:
  results: list[dict[str, Any]] = []
  if useLlm and parallel and len(roster) > 1:
    with ThreadPoolExecutor(max_workers=min(AGRI_MAX_WORKERS, len(roster))) as pool:
      futures = {
        pool.submit(
          _resolveOneAgri,
          agent,
          mediatorState,
          coeffKit,
          yearMonth,
          events,
          decree,
          useLlm,
        ): agent
        for agent in roster
      }
      for future in as_completed(futures):
        results.append(future.result())
    order = {agent["agentId"]: index for index, agent in enumerate(roster)}
    results.sort(key=lambda item: order.get(item["agentId"], 999))
  else:
    for agent in roster:
      results.append(
        _resolveOneAgri(agent, mediatorState, coeffKit, yearMonth, events, decree, useLlm)
      )

  byArea: dict[str, dict[str, Any]] = {
    areaId: {"farmerEffort": 1.0, "merchantShip": 1.0, "warehouseCare": 1.0, "note": "steady"}
    for areaId in AREA_IDS
  }
  millerBoost = 0.0
  millerCount = 0
  leak = 0.0
  rumors: list[str] = []
  for item, agent in zip(results, roster):
    areaId = item["areaId"]
    roleId = item["roleId"]
    effort = float(item["effort"])
    if roleId == "farmer":
      byArea[areaId]["farmerEffort"] = effort
    elif roleId == "merchant":
      byArea[areaId]["merchantShip"] = effort
    elif roleId == "warehouse":
      byArea[areaId]["warehouseCare"] = effort
    elif roleId == "miller":
      millerBoost += effort
      millerCount += 1
    leak += float(item["blackMarketLeak"])
    rumors.append(str(item["rumor"]))
    agent["lastRumor"] = str(item["rumor"])[:MEMORY_KEEP]
    agent["lastStance"] = str(item["stance"])
    tired = 1.0 if effort > 1.15 else 0.0
    agent["fatigue"] = _clamp01(float(agent.get("fatigue") or 0.0) * 0.7 + tired * 0.3)
    notes = str(byArea[areaId].get("note") or "steady")
    if item["stance"] not in ("fair", "steady"):
      byArea[areaId]["note"] = item["stance"]
    else:
      byArea[areaId]["note"] = notes

  millerMean = (millerBoost / millerCount) if millerCount else 1.0
  processNudge = (millerMean - 1.0) * MILLER_BLEND
  leakMean = leak / max(len(results), 1)
  routeCosts, routeCaps = routeMapsForMonth(yearMonth)
  return {
    "active": True,
    "source": "llm" if useLlm else "dry_run",
    "areaAgents": byArea,
    "processBeansNudge": round(processNudge, 4),
    "blackMarketLeak": round(leakMean * LEAK_SCALE, 4),
    "routeCosts": {f"{a}>{b}": cost for (a, b), cost in routeCosts.items()},
    "routeCaps": {f"{a}>{b}": cap for (a, b), cap in routeCaps.items()},
    "rumors": rumors[:12],
    "agents": [
      {
        "agentId": item["agentId"],
        "roleId": item["roleId"],
        "areaId": item["areaId"],
        "effort": round(float(item["effort"]), 3),
        "leak": round(float(item["blackMarketLeak"]), 3),
        "stance": item["stance"],
        "rumor": item["rumor"],
        "source": item.get("source", ""),
      }
      for item in results
    ],
  }


def applyAgriLeaks(economy: Any, leakRatio: float) -> None:
  if leakRatio <= 0:
    return
  drain = min(max(leakRatio, 0.0), 0.12)
  economy.foodBuffer = max(float(economy.foodBuffer) * (1.0 - drain), 0.0)
  if hasattr(economy, "sugarStock"):
    economy.sugarStock = max(float(economy.sugarStock) * (1.0 - drain * 0.5), 0.0)


def planAreaAgents(
  mediatorState: dict[str, Any],
  coeffKit: dict[str, float] | None = None,
  yearMonth: str = "1603-06",
) -> dict[str, dict[str, float | str]]:
  """Dry-run area intents (tests / callers that do not want the full block)."""
  meta: dict[str, Any] = {}
  roster = ensureAgriRoster(meta)
  block = resolveAgriLogistics(
    roster,
    mediatorState,
    coeffKit or {},
    yearMonth,
    [],
    "",
    useLlm=False,
    parallel=False,
  )
  return block["areaAgents"]


def pairKey(text: str) -> tuple[str, str] | None:
  if ">" not in text:
    return None
  left, right = text.split(">", 1)
  return left, right
