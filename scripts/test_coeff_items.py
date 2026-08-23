"""Smoke tests for coefficient items and agri/logistics agents."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.agri_logistics_agents import planAreaAgents
from src.law_and_policy import PolicyPackage
from src.mediators import applyShockDict, ensureMediators, runAgricultureAndLogistics
from src.policies import loadPolicyCatalog
from src.policy_items import (
  KIT_AGRI,
  KIT_INFLATE_BRAKE,
  applyItemToKit,
  applyMintBrake,
  classifyKit,
  clampActivatedIds,
  dealPolicyHand,
  decayCoeffKit,
  emptyCoeffKit,
  itemShock,
)


def main() -> int:
  catalog = loadPolicyCatalog()
  assert "okumai_relief" in catalog
  assert classifyKit(catalog["okumai_relief"]) == KIT_AGRI
  assert classifyKit(catalog["dodge_line"]) == KIT_INFLATE_BRAKE

  edoHand = dealPolicyHand("1635-06", None)
  assert "sankin_kotai" in [item.policyId for item in edoHand]
  laterHand = dealPolicyHand("1889-01", None)
  assert len(laterHand) == 8
  ids = [item.policyId for item in laterHand]

  clamped = clampActivatedIds(
    ["okumai_relief", "statute_missing", "sankin_kotai", "statute_187709_ab050a90"],
    laterHand,
    catalog,
  )
  assert "okumai_relief" in clamped
  assert "statute_missing" not in clamped
  assert all(not item.startswith("statute_") or item in ids for item in clamped)

  kit = emptyCoeffKit()
  applyItemToKit(kit, KIT_INFLATE_BRAKE)
  applyItemToKit(kit, KIT_INFLATE_BRAKE)
  assert kit["mintBrake"] > 0.1
  decayCoeffKit(kit)
  assert kit["mintBrake"] < 0.16

  policy = PolicyPackage(reserveMintingRatio=0.2)
  applyMintBrake(policy, {"mintBrake": 0.5})
  assert policy.reserveMintingRatio == 0.1

  shock = itemShock(KIT_INFLATE_BRAKE, catalog["dodge_line"])
  assert shock["fiatTrustShock"] < 0

  meta: dict = {}
  state = ensureMediators(meta, 1000.0)
  state["areas"]["tohoku_rim"]["landPollution"] = 0.4
  state["areas"]["edo_core"]["infraDamage"] = 0.3
  agents = planAreaAgents(state, {"harvestBoost": 0.05, "transferBoost": 0.1, "spoilCut": 0.05})
  assert agents["tohoku_rim"]["farmerEffort"] < agents["osaka_hub"]["farmerEffort"]
  state["national"]["fiatTrust"] = 0.7
  applyShockDict(state, {"targetArea": "ALL", "fiatTrustShock": -0.1})
  assert state["national"]["fiatTrust"] >= 0.79

  rice, food, snap = runAgricultureAndLogistics(
    state,
    1000.0,
    50.0,
    80.0,
    coeffKit={"harvestBoost": 0.05, "transferBoost": 0.2, "spoilCut": 0.0},
    areaAgents=agents,
  )
  assert rice > 0
  assert "areaAgents" in snap
  assert "coeffKit" in snap
  print("test_coeff_items: OK", f"hand={len(laterHand)} rice={rice:.1f}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
