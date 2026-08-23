"""Validate data/events CSV + YAML consistency."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.events import (  # noqa: E402
  EVENT_TABLE,
  MONTHLY_EVENTS,
  getEventPayload,
  getEventsForMonth,
  reloadEventData,
)


def main() -> int:
  reloadEventData()
  months = len(MONTHLY_EVENTS)
  catalogSize = len(EVENT_TABLE)
  print(f"months_with_events={months} catalog={catalogSize}")

  # Spot checks from migrated data
  assert "tenmei_famine_1" in getEventsForMonth("1782-01")
  assert "tenmei_famine_2" in getEventsForMonth("1783-07")
  assert "asama_eruption" in getEventsForMonth("1783-08")
  assert "kanei_famine" in getEventsForMonth("1642-05")
  assert "isewan_typhoon" in getEventsForMonth("1959-09")
  assert "dog_fullwater" in getEventsForMonth("1742-08")
  assert "perry_arrival" in getEventsForMonth("1853-07")
  assert "hoei_fuji_eruption_2" in getEventsForMonth("1707-12")
  assert "unzen_tsunami" in getEventsForMonth("1792-05")
  assert "sakurajima_taisho" in getEventsForMonth("1914-01")
  assert "ansei_cholera" in getEventsForMonth("1858-07")
  assert "first_railway" in getEventsForMonth("1872-10")
  hoeFuji = getEventPayload("hoei_fuji_eruption_2")
  assert hoeFuji is not None and hoeFuji.disasterOverride is not None
  assert hoeFuji.disasterOverride <= 0.45
  cholera = getEventPayload("ansei_cholera")
  assert cholera is not None and cholera.epidemicSeverity >= 0.4
  rail = getEventPayload("first_railway")
  assert rail is not None and not rail.disasterOverride
  assert "dutch_perry_warning" in getEventsForMonth("1852-07")

  tenmei = getEventPayload("tenmei_famine_1")
  assert tenmei is not None and tenmei.disasterOverride is not None
  assert tenmei.disasterOverride < 0.5
  assert getEventPayload("tenmei_famine") is not None

  # World + bridge lag
  assert "haitian_revolution_sugar" in getEventsForMonth("1791-08")
  assert "haitian_revolution_sugar" in getEventsForMonth("1792-01")
  assert "wall_street_crash" in getEventsForMonth("1929-10")
  assert "opec_embargo" in getEventsForMonth("1973-10")
  assert "covid_wuhan_alert" in getEventsForMonth("2019-12")
  assert "covid_wuhan_alert" in getEventsForMonth("2020-01")
  assert "chatgpt_chip_boom" in getEventsForMonth("2022-12")
  assert "middle_east_naphtha_squeeze" in getEventsForMonth("2025-07")
  assert "sim_horizon_2026_08" in getEventsForMonth("2026-08")

  chip = getEventPayload("chatgpt_chip_boom")
  assert chip is not None and chip.worldEffect == "chip_spike"

  perry = getEventPayload("perry_arrival")
  assert perry is not None
  assert perry.worldEffect == "sugar_spike"

  dutch = getEventPayload("dutch_perry_warning")
  assert dutch is not None
  assert "オランダ" in dutch.promptForLeader

  assert "shimabara_rebellion_01" in getEventsForMonth("1637-12")
  assert "edo_shogunate_starts" in getEventsForMonth("1603-03")
  from src.policies import historicalPoliciesForMonth, listAvailablePolicies, loadPolicyCatalog

  assert "okumai_relief" in loadPolicyCatalog()
  assert len(loadPolicyCatalog()) > 1000
  assert any(item.policyId.startswith("statute_") for item in loadPolicyCatalog().values())
  assert any(item.policyId == "sankin_kotai" for item in historicalPoliciesForMonth("1635-06"))
  assert any(item.policyId == "okumai_relief" for item in listAvailablePolicies("1707-12"))
  hoe = getEventPayload("hoei_fuji_eruption_2")
  assert hoe is not None and hoe.landPollution > 0.0
  assert hoe.targetArea in ("edo_core", "ALL")

  haiti = getEventPayload("haitian_revolution_sugar")
  assert haiti is not None
  assert haiti.scope == "world"
  assert haiti.worldEffect == "sugar_spike"

  worldCount = sum(1 for payload in EVENT_TABLE.values() if payload.scope == "world")
  assert worldCount >= 45, f"expected sparse-but-filled world catalog, got {worldCount}"

  print("validate_events: OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
