"""Build a compare.html zip: historical stats + event notes, no recap/speech."""

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
  "opinionLeaders",
  "agriLogistics",
  "llm",
)


def defaultSourceLog() -> Path:
  folder = ROOT / "logs" / "runs" / "historical_1603_2026" / "monthly.jsonl"
  flat = ROOT / "logs" / "runs" / "historical_1603_2026.jsonl"
  if folder.is_file():
    return folder
  if flat.is_file():
    return flat
  raise FileNotFoundError(
    "logs/runs/historical_1603_2026.jsonl (or folder monthly.jsonl) is missing"
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


def slimRow(row: dict, baselineFoodYen: float | None) -> tuple[dict, float]:
  from src.purchasing_power import computePurchasingPower, foodYenPerCapita

  out = {key: value for key, value in row.items() if key not in DROP_KEYS}
  events = [str(item) for item in (row.get("events") or [])]
  visible = [eventId for eventId in events if eventId not in NOISE_EVENT_IDS]
  out["events"] = visible
  out["eventNotes"] = [formatEventNote(eventId) for eventId in visible]
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


def writeZip(source: Path, dest: Path, start: str, end: str) -> dict:
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
  launch = {
    "standard": "historical",
    "start": firstYm,
    "end": lastYm,
    "useLlm": False,
    "historicalPolicy": True,
    "pack": "stats_events_only",
  }
  with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("monthly.jsonl", "\n".join(slimLines) + "\n")
    archive.writestr("launch.json", json.dumps(launch, ensure_ascii=False, indent=2) + "\n")
  return {"months": monthCount, "start": firstYm, "end": lastYm, "zip": str(dest)}


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Zip historical monthly stats for /compare.html (no recap, no mascot)"
  )
  parser.add_argument("--log", type=Path, default=None)
  parser.add_argument(
    "--out",
    type=Path,
    default=ROOT / "logs" / "compare_export" / "historical_stats_1603_2026.zip",
  )
  parser.add_argument("--start", default="1603-01")
  parser.add_argument("--end", default="2026-08")
  args = parser.parse_args()
  source = args.log if args.log is not None else defaultSourceLog()
  if not source.is_file():
    raise SystemExit(f"missing log: {source}")
  summary = writeZip(source, args.out, args.start, args.end)
  print(json.dumps(summary, ensure_ascii=False, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
