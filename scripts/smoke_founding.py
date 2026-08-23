"""Force-progress founding influence to verify multi-region Historical→Simulated flips."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.economy import EconomyState  # noqa: E402
from src.governance import GovernanceState, applyGovernance  # noqa: E402
from src.law_and_policy import LawAct, PolicyPackage, RulerDecision  # noqa: E402
from src.opinion_agents import (  # noqa: E402
  FOUNDING_INFLUENCE_THRESHOLD,
  REGION_CATALOG,
  applySimulatedRegionEffects,
  applySimulatedTaxPenalty,
  createDefaultRoster,
  decayRosterInfluence,
  updateRegionFounding,
)


def main() -> int:
  meta: dict = {}
  roster = createDefaultRoster()
  homes = {agent["agentId"]: agent["homeRegionId"] for agent in roster}
  assert homes["frontier_settler"] == "tohoku_rim", homes
  assert homes["cult_preacher"] == "edo_core", homes
  assert homes["merchant_traveler"] == "osaka_hub", homes

  for agent in roster:
    if agent["agentId"] in ("cult_preacher", "frontier_settler"):
      agent["mode"] = "founding"
      agent["influence"] = FOUNDING_INFLUENCE_THRESHOLD

  # Home bias: edo + tohoku founders flip those homes; Osaka only sees away weight.
  info = updateRegionFounding(meta, roster, "1783-08")
  assert info["mode"] == "simulated", info
  assert info["flippedThisMonth"] is True, info
  assert "edo_core" in info["flippedRegionIds"], info
  assert "tohoku_rim" in info["flippedRegionIds"], info
  assert "osaka_hub" not in info["flippedRegionIds"], info
  assert info["simulatedTaxShare"] >= 0.7, info

  for agent in roster:
    if agent["agentId"] == "merchant_traveler":
      agent["mode"] = "founding"
      agent["influence"] = float(REGION_CATALOG["osaka_hub"]["foundingThreshold"])
  info2 = updateRegionFounding(meta, roster, "1783-09")
  assert "osaka_hub" in info2["flippedRegionIds"], info2
  assert abs(info2["simulatedTaxShare"] - 1.0) < 1e-6, info2

  economy = EconomyState(year=1783, month=8)
  governance = GovernanceState(legitimacy=0.7)
  beforeFood = economy.foodBuffer
  beforeLeg = governance.legitimacy
  effects = applySimulatedRegionEffects(economy, governance, info2)
  assert economy.foodBuffer < beforeFood
  assert governance.legitimacy < beforeLeg
  assert effects["foodDrain"] > 0
  assert effects["simulatedRegionCount"] == len(REGION_CATALOG)

  decision = RulerDecision(
    law=LawAct(decree="test", taxRate=0.12),
    policy=PolicyPackage(),
  )
  effective = applyGovernance(
    decision, governance, "E2", economy.population, economy.foodBuffer, 100.0, []
  )
  beforeTax = effective.effectiveTaxRate
  applySimulatedTaxPenalty(effective, info2)
  assert effective.effectiveTaxRate < beforeTax
  assert "region_simulated" in effective.warnings

  hot = createDefaultRoster()
  hot[0]["influence"] = 0.4
  decayRosterInfluence(hot)
  assert hot[0]["influence"] < 0.4
  assert hot[0]["influence"] >= 0.05

  print(
    json.dumps(
      {
        "regions": info2["regions"],
        "effects": effects,
        "taxBefore": beforeTax,
        "taxAfter": effective.effectiveTaxRate,
      },
      ensure_ascii=False,
    )
  )
  print("smoke_founding: OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
