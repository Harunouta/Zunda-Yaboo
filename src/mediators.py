"""Agriculture / logistics mediators: area nodes + decaying intermediate shocks.

Founding regions (edo_core / osaka_hub / tohoku_rim) are reused as agri-logistics nodes.
Legacy catalog fields still load; they map into these mediators so old YAML keeps working.
"""

from __future__ import annotations

from typing import Any

from src.events import EventPayload

AREA_IDS = ("tohoku_rim", "edo_core", "osaka_hub")
AREA_ALIASES = {
  "all": "ALL",
  "japan": "ALL",
  "edo_core": "edo_core",
  "kanto": "edo_core",
  "edo": "edo_core",
  "tokyo": "edo_core",
  "tohoku_rim": "tohoku_rim",
  "tohoku": "tohoku_rim",
  "osaka_hub": "osaka_hub",
  "osaka": "osaka_hub",
  "kansai": "osaka_hub",
  "kinki": "osaka_hub",
  "kyushu": "osaka_hub",
  "west": "osaka_hub",
}
# Harvest / stock shares (sum 1.0).
AREA_SHARES = {
  "tohoku_rim": 0.25,
  "edo_core": 0.45,
  "osaka_hub": 0.30,
}
BASE_TRANSPORT = {
  ("edo_core", "tohoku_rim"): 0.06,
  ("tohoku_rim", "edo_core"): 0.06,
  ("edo_core", "osaka_hub"): 0.08,
  ("osaka_hub", "edo_core"): 0.08,
  ("tohoku_rim", "osaka_hub"): 0.12,
  ("osaka_hub", "tohoku_rim"): 0.12,
}
CONST_RECOVERY = 0.1
RATIO_DECAY = 0.6
FIAT_BASE = 1.0
MAX_TRANSFER_RATIO = 0.15
MAX_STATE = 1.0
KIT_SNAPSHOT_KEYS = (
  "harvestBoost",
  "transferBoost",
  "mintBrake",
  "trustRepair",
  "priceDamp",
  "spoilCut",
)


def normalizeArea(raw: str | None) -> str:
  key = str(raw or "ALL").strip().lower()
  return AREA_ALIASES.get(key, "ALL")


def emptyArea() -> dict[str, float]:
  return {
    "landPollution": 0.0,
    "infraDamage": 0.0,
    "riceStock": 0.0,
  }


def emptyNational() -> dict[str, float]:
  return {
    "laborDrain": 0.0,
    "socialUnrest": 0.0,
    "fiatTrust": FIAT_BASE,
    "stockSpoilage": 0.0,
    "govDemand": 0.0,
    "importCostShock": 0.0,
    "exportDrain": 0.0,
  }


def ensureMediators(meta: dict[str, Any], riceKoku: float) -> dict[str, Any]:
  state = meta.get("mediators")
  if not isinstance(state, dict):
    state = {}
  national = state.get("national")
  if not isinstance(national, dict):
    national = emptyNational()
  else:
    merged = emptyNational()
    merged.update({key: float(national.get(key, merged[key])) for key in merged})
    national = merged
  areas = state.get("areas")
  if not isinstance(areas, dict):
    areas = {}
  totalShare = 0.0
  for areaId in AREA_IDS:
    entry = areas.get(areaId)
    if not isinstance(entry, dict):
      entry = emptyArea()
      entry["riceStock"] = float(riceKoku) * AREA_SHARES[areaId]
    else:
      filled = emptyArea()
      filled.update({key: float(entry.get(key, filled[key])) for key in filled})
      entry = filled
    areas[areaId] = entry
    totalShare += float(entry.get("riceStock") or 0.0)
  if totalShare <= 1e-9 and riceKoku > 0:
    for areaId in AREA_IDS:
      areas[areaId]["riceStock"] = float(riceKoku) * AREA_SHARES[areaId]
  meta["mediators"] = {"national": national, "areas": areas}
  return meta["mediators"]


def decayMediators(state: dict[str, Any]) -> None:
  national = state["national"]
  national["stockSpoilage"] = 0.0
  national["govDemand"] = 0.0
  national["importCostShock"] = 0.0
  national["exportDrain"] = 0.0
  national["laborDrain"] = float(national["laborDrain"]) * RATIO_DECAY
  national["socialUnrest"] = float(national["socialUnrest"]) * RATIO_DECAY
  trust = float(national["fiatTrust"])
  national["fiatTrust"] = trust + (FIAT_BASE - trust) * (1.0 - RATIO_DECAY)
  for areaId in AREA_IDS:
    area = state["areas"][areaId]
    area["landPollution"] = max(float(area["landPollution"]) - CONST_RECOVERY, 0.0)
    area["infraDamage"] = max(float(area["infraDamage"]) - CONST_RECOVERY, 0.0)


def _addArea(state: dict[str, Any], areaId: str, fieldName: str, amount: float) -> None:
  if amount == 0.0:
    return
  targets = AREA_IDS if areaId == "ALL" else (areaId,)
  for target in targets:
    state["areas"][target][fieldName] = min(
      MAX_STATE,
      max(0.0, float(state["areas"][target][fieldName]) + amount),
    )


def _addNational(state: dict[str, Any], fieldName: str, amount: float) -> None:
  if amount == 0.0:
    return
  state["national"][fieldName] = min(
    MAX_STATE,
    max(0.0, float(state["national"][fieldName]) + amount),
  )


def _maxNational(state: dict[str, Any], fieldName: str, amount: float) -> None:
  if amount <= 0.0:
    return
  state["national"][fieldName] = min(
    MAX_STATE,
    max(float(state["national"][fieldName]), amount),
  )


def applyShockDict(state: dict[str, Any], shock: dict[str, Any]) -> None:
  areaId = normalizeArea(shock.get("targetArea"))
  _addArea(state, areaId, "landPollution", float(shock.get("landPollution") or 0.0))
  _addArea(state, areaId, "infraDamage", float(shock.get("infraDamage") or 0.0))
  _addNational(state, "laborDrain", float(shock.get("laborDrain") or 0.0))
  _addNational(state, "socialUnrest", float(shock.get("socialUnrest") or 0.0))
  _maxNational(state, "stockSpoilage", float(shock.get("stockSpoilage") or 0.0))
  _maxNational(state, "govDemand", float(shock.get("govDemand") or 0.0))
  _maxNational(state, "importCostShock", float(shock.get("importCostShock") or 0.0))
  _maxNational(state, "exportDrain", float(shock.get("exportDrain") or 0.0))
  fiatHit = float(shock.get("fiatTrustShock") or 0.0)
  if fiatHit != 0.0:
    state["national"]["fiatTrust"] = min(
      FIAT_BASE,
      max(0.05, float(state["national"]["fiatTrust"]) - fiatHit),
    )


def payloadToShock(payload: EventPayload) -> dict[str, Any]:
  return {
    "targetArea": payload.targetArea,
    "landPollution": payload.landPollution,
    "infraDamage": payload.infraDamage,
    "laborDrain": payload.laborDrain,
    "socialUnrest": payload.socialUnrest,
    "stockSpoilage": payload.stockSpoilage,
    "govDemand": payload.govDemand,
    "importCostShock": payload.importCostShock,
    "exportDrain": payload.exportDrain,
    "fiatTrustShock": payload.fiatTrustShock,
  }


def applyEventPayloads(state: dict[str, Any], payloads: list[EventPayload]) -> None:
  for payload in payloads:
    applyShockDict(state, payloadToShock(payload))


def runAgricultureAndLogistics(
  state: dict[str, Any],
  riceKoku: float,
  riceHarvest: float,
  foodBuffer: float,
  coeffKit: dict[str, float] | None = None,
  areaAgents: dict[str, dict[str, Any]] | None = None,
  routeCosts: dict[tuple[str, str], float] | None = None,
  routeCaps: dict[tuple[str, str], float] | None = None,
) -> tuple[float, float, dict[str, Any]]:
  """Split harvest by area, apply soil/spoil, then arbitrage rice across nodes."""
  national = state["national"]
  kit = coeffKit or {}
  agents = areaAgents or {}
  costs = routeCosts or {}
  caps = routeCaps or {}
  spoil = float(national["stockSpoilage"])
  spoil *= max(0.0, 1.0 - float(kit.get("spoilCut") or 0.0))
  labor = float(national["laborDrain"])
  harvestFactor = max(0.0, 1.0 - labor * 0.35) * (1.0 + float(kit.get("harvestBoost") or 0.0))
  harvestFactor = max(0.0, harvestFactor)
  areas = state["areas"]
  # Rebase stocks to current national rice, preserving relative shares.
  previous = sum(float(areas[areaId]["riceStock"]) for areaId in AREA_IDS)
  if previous <= 1e-9:
    for areaId in AREA_IDS:
      areas[areaId]["riceStock"] = riceKoku * AREA_SHARES[areaId]
  else:
    scale = riceKoku / previous
    for areaId in AREA_IDS:
      areas[areaId]["riceStock"] = float(areas[areaId]["riceStock"]) * scale

  for areaId in AREA_IDS:
    area = areas[areaId]
    agent = agents.get(areaId) or {}
    farmerEffort = float(agent.get("farmerEffort") or 1.0)
    warehouseCare = float(agent.get("warehouseCare") or 1.0)
    localHarvest = (
      riceHarvest
      * AREA_SHARES[areaId]
      * harvestFactor
      * farmerEffort
      * (1.0 - float(area["landPollution"]))
    )
    # National simulateMonth already added full harvest; replace with polluted local harvest.
    alreadyAdded = riceHarvest * AREA_SHARES[areaId]
    area["riceStock"] = max(float(area["riceStock"]) - alreadyAdded + localHarvest, 0.0)
    area["riceStock"] *= max(1.0 - spoil / max(warehouseCare, 0.45), 0.0)

  transfers: list[dict[str, Any]] = []
  for source in AREA_IDS:
    for dest in AREA_IDS:
      if source == dest:
        continue
      srcStock = float(areas[source]["riceStock"])
      destStock = float(areas[dest]["riceStock"])
      srcAvail = srcStock / AREA_SHARES[source]
      destAvail = destStock / AREA_SHARES[dest]
      infra = 0.5 * (float(areas[source]["infraDamage"]) + float(areas[dest]["infraDamage"]))
      baseCost = costs.get((source, dest), BASE_TRANSPORT[(source, dest)])
      cost = baseCost + infra
      if destAvail * (1.0 + cost) >= srcAvail:
        continue
      srcShip = float((agents.get(source) or {}).get("merchantShip") or 1.0)
      destShip = float((agents.get(dest) or {}).get("merchantShip") or 1.0)
      shipFactor = 0.5 * (srcShip + destShip) * (1.0 + float(kit.get("transferBoost") or 0.0))
      transferCap = MAX_TRANSFER_RATIO * max(shipFactor, 0.4) * float(caps.get((source, dest), 1.0))
      amount = min(srcStock * transferCap, (srcAvail - destAvail) * AREA_SHARES[dest] * 0.25)
      if amount <= 0.01:
        continue
      areas[source]["riceStock"] -= amount
      areas[dest]["riceStock"] += amount * max(1.0 - infra * 0.25, 0.5)
      transfers.append({"from": source, "to": dest, "amount": round(amount, 3)})

  newRice = sum(float(areas[areaId]["riceStock"]) for areaId in AREA_IDS)
  foodLoss = spoil * 0.25 + float(national["govDemand"]) * 0.08
  newFood = max(foodBuffer * (1.0 - foodLoss), 0.0)
  importShock = float(national["importCostShock"])
  exportDrain = float(national["exportDrain"])
  newRice = max(newRice * (1.0 - exportDrain * 0.12), 0.0)
  snapshot = {
    "national": {key: round(float(national[key]), 4) for key in national},
    "areas": {
      areaId: {
        "landPollution": round(float(areas[areaId]["landPollution"]), 4),
        "infraDamage": round(float(areas[areaId]["infraDamage"]), 4),
        "riceStock": round(float(areas[areaId]["riceStock"]), 2),
      }
      for areaId in AREA_IDS
    },
    "transfers": transfers,
    "importCostShock": round(importShock, 4),
    "coeffKit": {key: round(float(kit.get(key) or 0.0), 4) for key in KIT_SNAPSHOT_KEYS},
    "areaAgents": {
      areaId: {
        "farmerEffort": float((agents.get(areaId) or {}).get("farmerEffort") or 1.0),
        "merchantShip": float((agents.get(areaId) or {}).get("merchantShip") or 1.0),
        "warehouseCare": float((agents.get(areaId) or {}).get("warehouseCare") or 1.0),
        "note": str((agents.get(areaId) or {}).get("note") or "steady"),
      }
      for areaId in AREA_IDS
    },
  }
  return newRice, newFood, snapshot
