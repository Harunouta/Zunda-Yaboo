"""Dry-run tests for CSV agri catalog and logistics routes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.agri_catalog import loadAgriRoles, loadKitClasses, routeMapsForMonth
from src.agri_logistics_agents import ensureAgriRoster, resolveAgriLogistics
from src.mediators import ensureMediators


def main() -> int:
  roles = loadAgriRoles()
  assert len(roles) == 12
  kits = loadKitClasses()
  assert "inflateBrake" in kits
  costs1603, caps1603 = routeMapsForMonth("1603-01")
  assert ("edo_core", "osaka_hub") in costs1603
  assert caps1603[("edo_core", "osaka_hub")] <= 1.15
  costsRail, capsRail = routeMapsForMonth("1872-10")
  assert capsRail[("edo_core", "osaka_hub")] >= 1.5
  costs1964, caps1964 = routeMapsForMonth("1964-10")
  assert costs1964[("edo_core", "osaka_hub")] < costs1603[("edo_core", "osaka_hub")]
  assert caps1964[("edo_core", "osaka_hub")] >= capsRail[("edo_core", "osaka_hub")]

  meta: dict = {}
  state = ensureMediators(meta, 1000.0)
  roster = ensureAgriRoster(meta)
  assert len(roster) == 12
  block = resolveAgriLogistics(
    roster,
    state,
    {"harvestBoost": 0.05},
    "1783-08",
    ["asama_eruption"],
    "灰を払え",
    useLlm=False,
    parallel=False,
  )
  assert block["source"] == "dry_run"
  assert len(block["agents"]) == 12
  tohokuFarmer = next(item for item in block["agents"] if item["agentId"] == "tohoku_rim_farmer")
  assert tohokuFarmer["effort"] > 0.3
  print("test_agri_llm: OK", f"agents={len(block['agents'])} leak={block['blackMarketLeak']}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
