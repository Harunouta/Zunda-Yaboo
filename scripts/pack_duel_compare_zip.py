"""Build duel compare zip: stats + opinion + agri (no mascot / no decree text).

For /compare_duel.html — public-redistributable when sourced from --no-llm historical runs.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NOISE_EVENT_IDS = frozenset({"riot_risk", "region_simulated"})
DROP_KEYS = (
  "crowd",
  "behavior",
  "llm",
)


def formatEventNote(eventId: str) -> str:
  from src.events import EVENT_TABLE

  payload = EVENT_TABLE.get(eventId)
  notes = str(getattr(payload, "notes", "") or "").strip()
  leader = str(getattr(payload, "promptForLeader", "") or "").strip()
  detail = notes or leader
  if detail:
    oneLine = " ".join(detail.split())
    if len(oneLine) > 180:
      oneLine = oneLine[:179] + "…"
    return f"{eventId}: {oneLine}"
  return eventId


def slimOpinion(opinion: dict) -> dict:
  agents = []
  for agent in opinion.get("agents") or []:
    agents.append(
      {
        "agentId": agent.get("agentId"),
        "intent": agent.get("intent"),
        "mode": agent.get("mode"),
        "rumor": agent.get("rumor"),
      }
    )
  return {
    "abnormal": bool(opinion.get("abnormal")),
    "avgPanic": opinion.get("avgPanic"),
    "agents": agents,
  }


def slimAgri(agri: dict) -> dict:
  agents = []
  for agent in agri.get("agents") or []:
    agents.append(
      {
        "agentId": agent.get("agentId"),
        "areaId": agent.get("areaId"),
        "roleId": agent.get("roleId"),
        "displayName": agent.get("displayName"),
        "rumor": agent.get("rumor"),
      }
    )
  return {"agents": agents}


def slimRow(row: dict, baselineFoodYen: float | None) -> tuple[dict, float]:
  from src.purchasing_power import computePurchasingPower, foodYenPerCapita

  out = {key: value for key, value in row.items() if key not in DROP_KEYS}
  events = [str(item) for item in (row.get("events") or [])]
  visible = [eventId for eventId in events if eventId not in NOISE_EVENT_IDS]
  out["events"] = visible
  out["eventNotes"] = [formatEventNote(eventId) for eventId in visible]
  out["opinionLeaders"] = slimOpinion(row.get("opinionLeaders") or {})
  out["agriLogistics"] = slimAgri(row.get("agriLogistics") or {})
  prices = row.get("prices") or {}
  macro = row.get("macro") or {}
  yearMonth = str(row.get("yearMonth") or "")
  year = int(yearMonth[:4]) if yearMonth[:4].isdigit() else 1603
  population = float(macro.get("population") or 1.0)
  food = float(macro.get("foodBuffer") or 0.0) / max(population, 1.0)
  if baselineFoodYen is None:
    baselineFoodYen = foodYenPerCapita(food, year)
  purchasingPower = computePurchasingPower(
    zundaPrice=float(prices.get("zundaPrice") or 1.0),
    ankoPrice=float(prices.get("ankoPrice") or 1.0),
    azukiPrice=float(prices.get("azukiPrice") or 0.0),
    ricePrice=float(prices.get("ricePrice") or 1.0),
    foodPerCapita=food,
    goldSilverRatio=float(macro.get("goldSilverRatio") or prices.get("goldPrice") or 1.0),
    baselineFoodYen=baselineFoodYen,
    year=year,
  )
  out["purchasingPower"] = purchasingPower.toDict()
  law = dict(row.get("law") or {})
  law.pop("decree", None)
  out["law"] = law
  return out, baselineFoodYen


def writeZip(
  source: Path,
  dest: Path,
  start: str,
  end: str,
  label: str,
  standard: str,
) -> dict:
  dest.parent.mkdir(parents=True, exist_ok=True)
  slimLines: list[str] = []
  monthCount = 0
  firstYm = ""
  lastYm = ""
  baselineFoodYen: float | None = None
  with source.open("r", encoding="utf-8") as handle:
    for line in handle:
      if not line.strip():
        continue
      row = json.loads(line)
      yearMonth = str(row.get("yearMonth") or "")
      if start and yearMonth < start:
        continue
      if end and yearMonth > end:
        continue
      slim, baselineFoodYen = slimRow(row, baselineFoodYen)
      if not firstYm:
        firstYm = yearMonth
      lastYm = yearMonth
      slimLines.append(json.dumps(slim, ensure_ascii=False))
      monthCount += 1
  if monthCount == 0:
    raise ValueError("no months in range")
  resolvedStandard = standard or str(
    json.loads(slimLines[0]).get("monetaryStandard") or ""
  )
  launch = {
    "standard": resolvedStandard,
    "start": firstYm,
    "end": lastYm,
    "useLlm": False,
    "historicalPolicy": True,
    "pack": "duel_opinion_agri",
    "label": label or dest.stem,
  }
  with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("monthly.jsonl", "\n".join(slimLines) + "\n")
    archive.writestr("launch.json", json.dumps(launch, ensure_ascii=False, indent=2) + "\n")
  return {
    "months": monthCount,
    "start": firstYm,
    "end": lastYm,
    "standard": resolvedStandard,
    "zip": str(dest),
  }


def main() -> int:
  import sys

  sys.path.insert(0, str(ROOT))
  parser = argparse.ArgumentParser(
    description="Zip monthly duel stats for /compare_duel.html (opinion + agri, no mascot)"
  )
  parser.add_argument("--log", type=Path, required=True)
  parser.add_argument("--out", type=Path, required=True)
  parser.add_argument("--start", default="1603-01")
  parser.add_argument("--end", default="")
  parser.add_argument("--label", default="")
  parser.add_argument("--standard", default="")
  args = parser.parse_args()
  if not args.log.is_file():
    raise SystemExit(f"missing log: {args.log}")
  summary = writeZip(args.log, args.out, args.start, args.end, args.label, args.standard)
  print(json.dumps(summary, ensure_ascii=False, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
