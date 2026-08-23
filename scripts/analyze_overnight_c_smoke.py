"""Analyze overnight C crop smoke JSONL."""

import json
from pathlib import Path

from src.economy import EconomyState

path = Path("logs/runs/overnight_c_crop_smoke.jsonl")
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print("months", len(rows))
print("first", rows[0]["yearMonth"], "last", rows[-1]["yearMonth"])

harvestLike = []
for row in rows:
  macro = row["macro"]
  if macro.get("riceHarvest", 0) > 0 or macro.get("edamameHarvest", 0) > 5 or macro.get("azukiHarvest", 0) > 5:
    harvestLike.append(row)

print("\n--- sample harvest months (first 8) ---")
for row in harvestLike[:8]:
  macro = row["macro"]
  climate = row["climate"]
  print(
    f"{row['yearMonth']} ci={climate['index']:.3f} dm={climate['disasterMultiplier']:.3f} "
    f"riceH={macro['riceHarvest']:.1f} edaH={macro['edamameHarvest']:.1f} "
    f"azuH={macro['azukiHarvest']:.1f} edaS={macro['edamameStock']:.1f} azuS={macro['azukiStock']:.1f}"
  )

print("\n--- famine peak years Aug-Oct ---")
for yearMonth in ["1780-09", "1782-09", "1783-08", "1785-09", "1790-09"]:
  row = next(item for item in rows if item["yearMonth"] == yearMonth)
  macro = row["macro"]
  climate = row["climate"]
  print(
    f"{yearMonth} ci={climate['index']:.3f} dm={climate['disasterMultiplier']:.3f} "
    f"rice={macro['riceHarvest']:.1f} eda={macro['edamameHarvest']:.1f} azu={macro['azukiHarvest']:.1f} "
    f"stocks eda/azu={macro['edamameStock']:.1f}/{macro['azukiStock']:.1f}"
  )

pairs = []
for row in rows:
  macro = row["macro"]
  if macro["riceHarvest"] > 0:
    pairs.append(
      (
        row["climate"]["index"],
        macro["riceHarvest"],
        macro["edamameHarvest"],
        macro["azukiHarvest"],
      )
    )

climateIndexes = [pair[0] for pair in pairs]
riceHarvests = [pair[1] for pair in pairs]
edamameHarvests = [pair[2] for pair in pairs]
azukiHarvests = [pair[3] for pair in pairs]
print("\nrice-harvest months:", len(pairs))
print(f"climateIndex range {min(climateIndexes):.3f}..{max(climateIndexes):.3f}")
print(f"riceHarvest range {min(riceHarvests):.1f}..{max(riceHarvests):.1f}")
print(f"edamameHarvest range {min(edamameHarvests):.1f}..{max(edamameHarvests):.1f}")
print(f"azukiHarvest range {min(azukiHarvests):.1f}..{max(azukiHarvests):.1f}")

sameStockMonths = sum(
  1 for row in rows if abs(row["macro"]["edamameStock"] - row["macro"]["azukiStock"]) < 0.01
)
print(f"months with identical stocks: {sameStockMonths}/{len(rows)}")
last = rows[-1]
print(
  f"final stocks edamame={last['macro']['edamameStock']} azuki={last['macro']['azukiStock']} "
  f"riceKoku={last['macro']['riceKoku']}"
)
print(
  f"final prices z={last['prices']['zundaPrice']} a={last['prices']['ankoPrice']} "
  f"r={last['prices']['ricePrice']}"
)

goodMonths = [row for row in rows if row["climate"]["index"] >= 0.1 and row["macro"]["riceHarvest"] > 0]
badMonths = [row for row in rows if row["climate"]["index"] <= -0.1 and row["macro"]["riceHarvest"] > 0]


def averageHarvest(months: list, key: str) -> float:
  return sum(item["macro"][key] for item in months) / len(months)


if goodMonths and badMonths:
  print(
    f"\ngood ci months n={len(goodMonths)} avg rice/eda/azu = "
    f"{averageHarvest(goodMonths, 'riceHarvest'):.1f}/"
    f"{averageHarvest(goodMonths, 'edamameHarvest'):.1f}/"
    f"{averageHarvest(goodMonths, 'azukiHarvest'):.1f}"
  )
  print(
    f"bad  ci months n={len(badMonths)} avg rice/eda/azu = "
    f"{averageHarvest(badMonths, 'riceHarvest'):.1f}/"
    f"{averageHarvest(badMonths, 'edamameHarvest'):.1f}/"
    f"{averageHarvest(badMonths, 'azukiHarvest'):.1f}"
  )

# Crop sensitivity check: same climate, different yields
from src.economy import (
  AZUKI_BASE_YIELD,
  AZUKI_CLIMATE_SENSITIVITY,
  AZUKI_COLD_PENALTY,
  EDAMAME_BASE_YIELD,
  EDAMAME_CLIMATE_SENSITIVITY,
  EDAMAME_COLD_PENALTY,
  RICE_BASE_YIELD,
  RICE_CLIMATE_SENSITIVITY,
  RICE_COLD_PENALTY,
  cropYield,
)

climateIndex = -0.2
disasterMultiplier = 0.8
print("\nformula check climateIndex=-0.2 disaster=0.8:")
print(" rice", round(cropYield(RICE_BASE_YIELD, climateIndex, disasterMultiplier, RICE_CLIMATE_SENSITIVITY, RICE_COLD_PENALTY), 2))
print(" edamame", round(cropYield(EDAMAME_BASE_YIELD, climateIndex, disasterMultiplier, EDAMAME_CLIMATE_SENSITIVITY, EDAMAME_COLD_PENALTY), 2))
print(" azuki", round(cropYield(AZUKI_BASE_YIELD, climateIndex, disasterMultiplier, AZUKI_CLIMATE_SENSITIVITY, AZUKI_COLD_PENALTY), 2))
climateIndex = 0.2
disasterMultiplier = 1.0
print("formula check climateIndex=+0.2 disaster=1.0:")
print(" rice", round(cropYield(RICE_BASE_YIELD, climateIndex, disasterMultiplier, RICE_CLIMATE_SENSITIVITY, RICE_COLD_PENALTY), 2))
print(" edamame", round(cropYield(EDAMAME_BASE_YIELD, climateIndex, disasterMultiplier, EDAMAME_CLIMATE_SENSITIVITY, EDAMAME_COLD_PENALTY), 2))
print(" azuki", round(cropYield(AZUKI_BASE_YIELD, climateIndex, disasterMultiplier, AZUKI_CLIMATE_SENSITIVITY, AZUKI_COLD_PENALTY), 2))

legacy = EconomyState.fromDict({"year": 1603, "month": 1, "rawBeans": 100})
print(f"\nmigration rawBeans=100 -> edamame={legacy.edamameStock} azuki={legacy.azukiStock} raw={legacy.rawBeans}")

path1853 = Path("logs/runs/overnight_c_1853_smoke.jsonl")
if path1853.exists():
  rows1853 = [json.loads(line) for line in path1853.read_text(encoding="utf-8").splitlines() if line.strip()]
  print(f"\n1853 smoke months={len(rows1853)} has crop fields={('edamameStock' in rows1853[0]['macro'])}")
  sep = rows1853[8]  # September
  print(
    f"1853-09 ci={sep['climate']['index']} riceH={sep['macro']['riceHarvest']} "
    f"edaH={sep['macro']['edamameHarvest']} azuH={sep['macro']['azukiHarvest']}"
  )
