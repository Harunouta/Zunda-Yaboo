"""Purchasing-power helpers: map sim prices to modern-yen story metrics.

Bridge is rice PPP (purchasing-power parity):
  1.0 sim ricePrice unit ≈ SIM_RICE_UNIT_KG of retail rice in modern Japan.
  zunda / anko / azuki / metal are converted through that rice bridge.

Numbers are deliberately illustrative for viewing — not scholarly CPI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


# Modern Japan retail rice (ordinary polished), ~2024-2026 yen/kg.
YEN_PER_KG_RICE = 450.0
# One unit of sim ricePrice ≈ this many kg.
SIM_RICE_UNIT_KG = 1.0
# Treat sim foodBuffer units as a stock, not kg. 0.03 ≈ one month of mouths.
BASE_FOOD_UNIT = 0.03
REF_STOCK_MONTHS = 6.0
STOCK_SCARCITY_FLOOR = 0.2
STOCK_SCARCITY_CEIL = 1.8
# Illustrative monthly food basket in modern yen by era (viewing, not CPI).
ERA_FOOD_BASKET: list[tuple[int, float]] = [
  (1603, 520.0),
  (1783, 480.0),
  (1868, 2800.0),
  (1945, 1600.0),
  (1960, 16000.0),
  (1991, 34000.0),
  (2026, 39000.0),
]
MODERN_FOOD_YEN_PER_CAPITA_MONTH = 40_000.0
# Classical schoolbook mapping: 1 ryo ≈ 1 koku ≈ 150 kg rice (very rough).
KG_PER_KOKU = 150.0
# Silver monme → rice kg proxy when gold/silver ratio is near 1 (illustrative).
MONME_PER_KG_RICE_PROXY = 60.0

EPS = 1e-9


@dataclass
class PurchasingPower:
  yenPerRiceUnit: float
  zundaYen: float
  ankoYen: float
  azukiYen: float
  foodYenPerCapita: float
  livingVsModern: float
  developmentIndex: float
  oneRyoYenApprox: float
  vibe: str
  method: str = "rice_ppp_modern_yen"
  dollarYen: float = 0.0
  fxYenPerDollar: float = 0.0

  def toDict(self) -> dict[str, Any]:
    payload = asdict(self)
    for key in (
      "yenPerRiceUnit",
      "zundaYen",
      "ankoYen",
      "azukiYen",
      "foodYenPerCapita",
      "livingVsModern",
      "developmentIndex",
      "oneRyoYenApprox",
      "dollarYen",
      "fxYenPerDollar",
    ):
      payload[key] = round(float(payload[key]), 4)
    return payload


def yenPerRiceUnit() -> float:
  return YEN_PER_KG_RICE * SIM_RICE_UNIT_KG


def riceRelativePrice(price: float, ricePrice: float) -> float:
  return float(price) / max(float(ricePrice), EPS)


def toModernYen(price: float, ricePrice: float) -> float:
  return riceRelativePrice(price, ricePrice) * yenPerRiceUnit()


def eraFoodBasketYen(year: int) -> float:
  if year <= ERA_FOOD_BASKET[0][0]:
    return ERA_FOOD_BASKET[0][1]
  if year >= ERA_FOOD_BASKET[-1][0]:
    return ERA_FOOD_BASKET[-1][1]
  for index in range(1, len(ERA_FOOD_BASKET)):
    leftYear, leftYen = ERA_FOOD_BASKET[index - 1]
    rightYear, rightYen = ERA_FOOD_BASKET[index]
    if leftYear <= year <= rightYear:
      span = max(rightYear - leftYear, 1)
      t = (year - leftYear) / span
      return leftYen + (rightYen - leftYen) * t
  return ERA_FOOD_BASKET[-1][1]


def stockMonthsFromFood(foodPerCapita: float) -> float:
  return max(float(foodPerCapita), 0.0) / BASE_FOOD_UNIT


def foodYenPerCapita(foodPerCapita: float, year: int = 1603) -> float:
  # Era basket (how rich the century is) times grain-stock tightness.
  stockMonths = stockMonthsFromFood(foodPerCapita)
  scarcity = min(max(stockMonths / REF_STOCK_MONTHS, STOCK_SCARCITY_FLOOR), STOCK_SCARCITY_CEIL)
  return eraFoodBasketYen(year) * scarcity


def oneRyoYenApprox(goldSilverRatio: float = 1.0) -> float:
  # Scale lightly with gold/silver stress so metal runs still move.
  return KG_PER_KOKU * YEN_PER_KG_RICE * max(float(goldSilverRatio), 0.2)


def livingVsModernRatio(foodYen: float) -> float:
  return float(foodYen) / MODERN_FOOD_YEN_PER_CAPITA_MONTH


def developmentIndex(foodYen: float, baselineFoodYen: float) -> float:
  return float(foodYen) / max(float(baselineFoodYen), EPS)


def vibeLabel(livingVsModern: float, development: float) -> str:
  if livingVsModern >= 0.45:
    return "現代に近い食のゆとり"
  if development >= 2.5 and livingVsModern >= 0.05:
    return "こんなに経済発展した！"
  if development >= 1.6:
    return "発展してきた"
  if livingVsModern < 0.015:
    return "こんなしょぼい！！"
  if livingVsModern < 0.04:
    return "まだ貧しい"
  if development < 0.85:
    return "創業時より厳しい"
  return "そこそこ"


def computePurchasingPower(
  *,
  zundaPrice: float,
  ankoPrice: float,
  ricePrice: float,
  foodPerCapita: float,
  goldSilverRatio: float = 1.0,
  baselineFoodYen: float | None = None,
  dollarPrice: float = 1.0,
  fxYenPerDollar: float = 0.0,
  azukiPrice: float = 0.0,
  year: int = 1603,
) -> PurchasingPower:
  foodYen = foodYenPerCapita(foodPerCapita, year)
  baseline = float(baselineFoodYen) if baselineFoodYen is not None else foodYen
  living = livingVsModernRatio(foodYen)
  development = developmentIndex(foodYen, baseline)
  fx = float(fxYenPerDollar)
  dollarYen = float(dollarPrice) * fx if fx > 0 else 0.0
  return PurchasingPower(
    yenPerRiceUnit=yenPerRiceUnit(),
    zundaYen=toModernYen(zundaPrice, ricePrice),
    ankoYen=toModernYen(ankoPrice, ricePrice),
    azukiYen=toModernYen(azukiPrice, ricePrice) if azukiPrice > 0 else 0.0,
    foodYenPerCapita=foodYen,
    livingVsModern=living,
    developmentIndex=development,
    oneRyoYenApprox=oneRyoYenApprox(goldSilverRatio),
    dollarYen=dollarYen,
    fxYenPerDollar=fx,
    vibe=vibeLabel(living, development),
    method="era_basket_times_grain_stock",
  )


def summarizeEra(
  rows: list[dict[str, Any]],
  *,
  baselineFoodYen: float | None = None,
) -> list[dict[str, Any]]:
  """Build yearly median PPP rows from monthly JSONL-like dicts."""
  from statistics import median

  byYear: dict[str, list[PurchasingPower]] = {}
  resolvedBaseline = baselineFoodYen
  for row in rows:
    yearMonth = str(row.get("yearMonth") or "")
    if len(yearMonth) < 4:
      continue
    year = int(yearMonth[:4])
    if resolvedBaseline is None:
      resolvedBaseline = foodYenPerCapita(food, year)
    existing = row.get("purchasingPower")
    if isinstance(existing, dict) and "foodYenPerCapita" in existing:
      # Recompute vibe/development against a stable baseline when exporting.
      pp = computePurchasingPower(
        zundaPrice=float(prices.get("zundaPrice") or existing.get("zundaYen") or 1.0),
        ankoPrice=float(prices.get("ankoPrice") or 1.0),
        azukiPrice=float(prices.get("azukiPrice") or 0.0),
        ricePrice=float(prices.get("ricePrice") or 1.0),
        foodPerCapita=food,
        goldSilverRatio=float(macro.get("goldSilverRatio") or prices.get("goldPrice") or 1.0),
        baselineFoodYen=resolvedBaseline,
        year=year,
      )
    else:
      pp = computePurchasingPower(
        zundaPrice=float(prices.get("zundaPrice") or 1.0),
        ankoPrice=float(prices.get("ankoPrice") or 1.0),
        azukiPrice=float(prices.get("azukiPrice") or 0.0),
        ricePrice=float(prices.get("ricePrice") or 1.0),
        foodPerCapita=food,
        goldSilverRatio=float(macro.get("goldSilverRatio") or prices.get("goldPrice") or 1.0),
        baselineFoodYen=resolvedBaseline,
        year=year,
      )
    byYear.setdefault(year, []).append(pp)

  out: list[dict[str, Any]] = []
  for year in sorted(byYear):
    items = byYear[year]
    foodMed = median(item.foodYenPerCapita for item in items)
    livingMed = median(item.livingVsModern for item in items)
    devMed = median(item.developmentIndex for item in items)
    out.append(
      {
        "year": int(year),
        "zundaYen": round(median(item.zundaYen for item in items), 2),
        "ankoYen": round(median(item.ankoYen for item in items), 2),
        "azukiYen": round(median(item.azukiYen for item in items), 2),
        "foodYenPerCapita": round(foodMed, 2),
        "livingVsModernPct": round(livingMed * 100.0, 3),
        "developmentIndex": round(devMed, 3),
        "oneRyoYenApprox": round(median(item.oneRyoYenApprox for item in items), 1),
        "vibe": vibeLabel(livingMed, devMed),
      }
    )
  return out
