"""Write tiny synthetic duel zips for public compare_duel.html smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "redistributable" / "duel_packs"

OPINION_IDS = [
  "elder_village",
  "merchant_traveler",
  "cult_preacher",
  "smuggler_broker",
  "frontier_settler",
]
AREAS = ["tohoku_rim", "edo_core", "osaka_hub"]
ROLES = ["farmer", "merchant", "warehouse", "miller"]


def monthRow(year: int, month: int, standard: str, side: str) -> dict:
  ym = f"{year:04d}-{month:02d}"
  primaryField = "zundaPrice" if standard == "zunda" else "azukiPrice"
  basePrice = 1.1 if standard == "zunda" else 0.9
  pop = 12000.0 if side == "a" else 11000.0
  return {
    "yearMonth": ym,
    "year": year,
    "month": month,
    "monetaryStandard": standard,
    "events": ["sample_duel_demo"] if month == 7 else [],
    "eventNotes": ["sample_duel_demo: デモ用イベント"] if month == 7 else [],
    "macro": {"population": pop + month * 3, "foodBuffer": pop * 0.2},
    "prices": {
      "ricePrice": 1.0,
      primaryField: basePrice + month * 0.01,
      "zundaPrice": 1.1,
      "ankoPrice": 1.0,
      "azukiPrice": 0.9,
    },
    "purchasingPower": {
      "foodYenPerCapita": 800.0 + month,
      "livingVsModern": 0.4,
      "method": "demo",
    },
    "historicalFidelity": {"score": 0.75},
    "law": {},
    "opinionLeaders": {
      "abnormal": month == 7,
      "avgPanic": 0.72 if month == 7 else 0.4,
      "agents": [
        {
          "agentId": agentId,
          "intent": "black_market" if month == 7 else "comply",
          "rumor": f"[{side}/{standard}] {agentId} のデモ噂 {ym}",
        }
        for agentId in OPINION_IDS
      ],
    },
    "agriLogistics": {
      "agents": [
        {
          "agentId": f"{areaId}_{roleId}",
          "areaId": areaId,
          "roleId": roleId,
          "displayName": f"{areaId} {roleId}",
          "rumor": f"[{side}] {areaId}/{roleId} デモ {ym}",
        }
        for areaId in AREAS
        for roleId in ROLES
      ],
    },
  }


def writeSample(standard: str, side: str, dest: Path) -> None:
  from scripts.pack_duel_compare_zip import writeZip

  tmp = ROOT / "logs" / f"_duel_sample_{side}.jsonl"
  tmp.parent.mkdir(parents=True, exist_ok=True)
  lines = []
  for year in (1603, 1604):
    for month in range(1, 13):
      lines.append(json.dumps(monthRow(year, month, standard, side), ensure_ascii=False))
  tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
  writeZip(tmp, dest, "1603-01", "1604-12", dest.stem, standard)
  tmp.unlink(missing_ok=True)


def main() -> int:
  import sys

  sys.path.insert(0, str(ROOT))
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  writeSample("zunda", "a", OUT_DIR / "sample_zunda_1603_1604.zip")
  writeSample("azuki", "b", OUT_DIR / "sample_azuki_1603_1604.zip")
  print(json.dumps({"out": str(OUT_DIR), "files": 2}, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
