"""Dry-run windows around imported volcano / epidemic / infra events.

Checks edo_metal --historical-policy first, then zunda and anko fallbacks.
Does not call LM Studio. Does not overwrite tonight_* archives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.events import (  # noqa: E402
  getEventPayload,
  getEventsForMonth,
  reloadEventData,
)
from src.monthly_engine import runMonthlySimulation  # noqa: E402

LOG_DIR = ROOT / "logs" / "runs"


def pickRow(path: Path, yearMonth: str) -> dict:
  for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
      continue
    row = json.loads(line)
    if row.get("yearMonth") == yearMonth:
      return row
  raise AssertionError(f"missing month {yearMonth} in {path}")


def runWindow(
  name: str,
  start: str,
  end: str,
  standard: str,
  historicalPolicy: bool,
) -> Path:
  logPath = LOG_DIR / f"{name}.jsonl"
  LOG_DIR.mkdir(parents=True, exist_ok=True)
  runMonthlySimulation(
    standard=standard,
    start=start,
    end=end,
    useLlm=False,
    resume=False,
    historicalPolicy=historicalPolicy,
    logPath=logPath,
    opinionLeaderCount=0,
    opinionParallel=False,
  )
  return logPath


def assertFired(yearMonth: str, eventId: str) -> None:
  events = getEventsForMonth(yearMonth)
  assert eventId in events, f"{eventId} missing in {yearMonth}: {events}"


def assertRiceUp(eventRow: dict, quietRow: dict, label: str) -> None:
  eventRice = float((eventRow.get("prices") or {}).get("ricePrice") or 0)
  quietRice = float((quietRow.get("prices") or {}).get("ricePrice") or 0)
  assert eventRice > quietRice * 1.08, (
    f"{label}: rice did not rise ({quietRice:.4f} -> {eventRice:.4f})"
  )


def assertFoodDown(eventRow: dict, quietRow: dict, label: str) -> None:
  eventFood = float((eventRow.get("macro") or {}).get("foodBuffer") or 0)
  quietFood = float((quietRow.get("macro") or {}).get("foodBuffer") or 0)
  assert eventFood < quietFood, f"{label}: foodBuffer did not fall ({quietFood} -> {eventFood})"


def assertRiceStable(eventRow: dict, quietRow: dict, label: str) -> None:
  eventRice = float((eventRow.get("prices") or {}).get("ricePrice") or 0)
  quietRice = float((quietRow.get("prices") or {}).get("ricePrice") or 0)
  ratio = eventRice / max(quietRice, 1e-6)
  assert 0.85 <= ratio <= 1.2, f"{label}: infra should not shock rice ({quietRice:.4f} -> {eventRice:.4f})"


def checkCatalog() -> None:
  reloadEventData()
  assertFired("1707-12", "hoei_fuji_eruption_2")
  assertFired("1707-10", "hoei_earthquake")
  assertFired("1923-09", "great_kanto_earthquake")
  assertFired("2011-03", "tohoku_earthquake")
  assertFired("1657-03", "meireki_fire")
  assertFired("1792-05", "unzen_tsunami")
  assertFired("1914-01", "sakurajima_taisho")
  assertFired("1783-08", "asama_eruption")
  assertFired("1858-07", "ansei_cholera")
  assertFired("1872-10", "first_railway")
  hoe = getEventPayload("hoei_fuji_eruption_2")
  assert hoe is not None and hoe.disasterOverride is not None and hoe.disasterOverride <= 0.45
  cholera = getEventPayload("ansei_cholera")
  assert cholera is not None and cholera.epidemicSeverity >= 0.4
  rail = getEventPayload("first_railway")
  assert rail is not None and rail.disasterOverride is None
  print("catalog spot checks: OK")


def checkStandard(standard: str, historicalPolicy: bool) -> None:
  tag = f"{standard}_{'hist' if historicalPolicy else 'dry'}"
  # Hoei Fuji: 1707-11 quiet-ish vs 1707-12 event (Hoei earthquake sheet is not imported).
  hoeLog = runWindow(f"smoke_hoei_{tag}", "1707-09", "1707-12", standard, historicalPolicy)
  quiet = pickRow(hoeLog, "1707-09")
  event = pickRow(hoeLog, "1707-12")
  assert "hoei_fuji_eruption_2" in (event.get("events") or [])
  assertRiceUp(event, quiet, f"{tag} hoei rice")
  assertFoodDown(event, quiet, f"{tag} hoei food")

  sakuraLog = runWindow(f"smoke_sakurajima_{tag}", "1913-12", "1914-02", standard, historicalPolicy)
  quietS = pickRow(sakuraLog, "1913-12")
  eventS = pickRow(sakuraLog, "1914-01")
  assert "sakurajima_taisho" in (eventS.get("events") or [])
  assertRiceUp(eventS, quietS, f"{tag} sakurajima rice")

  choleraLog = runWindow(f"smoke_cholera_{tag}", "1858-06", "1858-08", standard, historicalPolicy)
  quietC = pickRow(choleraLog, "1858-06")
  eventC = pickRow(choleraLog, "1858-07")
  assert "ansei_cholera" in (eventC.get("events") or [])
  popC = float((eventC.get("macro") or {}).get("population") or 0)
  popQ = float((quietC.get("macro") or {}).get("population") or 0)
  assert popC < popQ, f"{tag} cholera: population did not fall"

  railLog = runWindow(f"smoke_rail_{tag}", "1872-09", "1872-11", standard, historicalPolicy)
  quietR = pickRow(railLog, "1872-09")
  eventR = pickRow(railLog, "1872-10")
  assert "first_railway" in (eventR.get("events") or [])
  assertRiceStable(eventR, quietR, f"{tag} railway")
  print(f"{tag}: OK")


def main() -> int:
  checkCatalog()
  checkStandard("edo_metal", True)
  checkStandard("zunda", False)
  checkStandard("anko", False)
  print("smoke_shaped_events: OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
