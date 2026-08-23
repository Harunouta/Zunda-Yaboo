"""Monthly economy physics for zunda / anko / azuki / edo_metal / dollar standards."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.governance import EnginePolicy


DAYS_PER_MONTH = 30
# ~2 month shelf life for fresh beans (was 0.1 → 100%/mo, stocks never persisted).
RAW_BEAN_SPOIL_MONTHS = 2.0
PROCESSED_ZUNDA_SPOIL_MONTHS = 3.0
ANKO_SPOIL_MONTHS = 6.0
DRY_AZUKI_SPOIL_MONTHS = 18.0
AZUKI_NOTE_MINT_RATIO = 0.35
SUGAR_PER_BEAN = 0.1
SUGAR_PER_ANKO = 0.15
PROCESSING_RATIO = 0.8
ANKO_PROCESSING_RATIO = 0.75
BASE_FOOD_CONSUMPTION = 0.03
MONTHLY_SUBSISTENCE = 0.032
POPULATION_FLOOR = 500.0

# Legacy shared harvest window (kept for callers / docs).
HARVEST_MONTHS = {8, 9, 10}
HARVEST_BASE = 520.0

# Per-crop harvest calendars (slightly staggered; readable toy model).
RICE_HARVEST_MONTHS = {8, 9, 10}
EDAMAME_HARVEST_MONTHS = {7, 8, 9}
AZUKI_HARVEST_MONTHS = {9, 10, 11}

# Base yield per harvest month (procedural overnight model; not real climate data).
RICE_BASE_YIELD = 520.0
EDAMAME_BASE_YIELD = 48.0
AZUKI_BASE_YIELD = 40.0

# ClimateIndex sensitivity: yield *= (1 + climateIndex * sens), floored.
RICE_CLIMATE_SENSITIVITY = 0.35
EDAMAME_CLIMATE_SENSITIVITY = 0.55
AZUKI_CLIMATE_SENSITIVITY = 0.45

# Extra cold-decade penalty when climateIndex < 0 (crop-specific).
RICE_COLD_PENALTY = 0.25
EDAMAME_COLD_PENALTY = 0.40
AZUKI_COLD_PENALTY = 0.30

# Off-season trickle so side markets never fully dry up.
OFF_SEASON_EDAMAME_TRICKLE = 3.0
OFF_SEASON_AZUKI_TRICKLE = 2.5

# Side-market auto-processing caps (edo_metal path).
SIDE_PROCESS_RATIO = 0.05
SIDE_PROCESS_CAP = 20.0
YIELD_FLOOR = 0.05


class MonetaryStandard(str, Enum):
  ZUNDA = "zunda"
  ANKO = "anko"
  AZUKI = "azuki"
  EDO_METAL = "edo_metal"
  GOLD_YEN = "gold_yen"
  DOLLAR = "dollar"


STANDARD_CHOICES = tuple(item.value for item in MonetaryStandard)


def getEpoch(year: int) -> str:
  if year < 1751:
    return "E1"
  if year < 1868:
    return "E2"
  if year < 1946:
    return "E3"
  return "E4"


@dataclass
class EconomyState:
  year: int
  month: int
  population: float = 12000.0
  foodBuffer: float = 2000.0
  sugarStock: float = 300.0
  # Legacy pool; kept in sync as edamameStock + azukiStock for old checkpoints / laws.
  rawBeans: float = 0.0
  edamameStock: float = 0.0
  azukiStock: float = 0.0
  processedZunda: float = 0.0
  zundaNotes: float = 0.0
  ankoReserve: float = 0.0
  ankoNotes: float = 0.0
  azukiNotes: float = 0.0
  riceKoku: float = 1000.0
  goldRyo: float = 200.0
  silverMonme: float = 4000.0
  hanSatsu: float = 500.0
  hanSatsuCredit: float = 1.0
  goldSilverRatio: float = 1.0
  dollarNotes: float = 0.0
  dollarReserves: float = 0.0
  fxYenPerDollar: float = 0.0
  monetaryStandard: MonetaryStandard = MonetaryStandard.ZUNDA
  climateIndex: float = 0.0

  @property
  def yearMonth(self) -> str:
    return f"{self.year:04d}-{self.month:02d}"

  def syncRawBeans(self) -> None:
    """Keep legacy rawBeans equal to the sum of crop stocks."""
    self.rawBeans = max(self.edamameStock, 0.0) + max(self.azukiStock, 0.0)

  def toDict(self) -> dict[str, Any]:
    self.syncRawBeans()
    data = asdict(self)
    data["monetaryStandard"] = self.monetaryStandard.value
    data["yearMonth"] = self.yearMonth
    return data

  @classmethod
  def fromDict(cls, data: dict[str, Any]) -> "EconomyState":
    standard = MonetaryStandard(data.get("monetaryStandard", "zunda"))
    legacyRaw = float(data.get("rawBeans", 0))
    hasEdamame = "edamameStock" in data
    hasAzuki = "azukiStock" in data
    if hasEdamame and hasAzuki:
      edamameStock = float(data["edamameStock"])
      azukiStock = float(data["azukiStock"])
    elif hasEdamame:
      edamameStock = float(data["edamameStock"])
      azukiStock = max(legacyRaw - edamameStock, 0.0)
    elif hasAzuki:
      azukiStock = float(data["azukiStock"])
      edamameStock = max(legacyRaw - azukiStock, 0.0)
    else:
      # Old checkpoints: split the shared bean pool evenly.
      edamameStock = legacyRaw * 0.5
      azukiStock = legacyRaw * 0.5
    state = cls(
      year=int(data["year"]),
      month=int(data["month"]),
      population=float(data.get("population", 12000)),
      foodBuffer=float(data.get("foodBuffer", 2000)),
      sugarStock=float(data.get("sugarStock", 300)),
      rawBeans=edamameStock + azukiStock,
      edamameStock=edamameStock,
      azukiStock=azukiStock,
      processedZunda=float(data.get("processedZunda", 0)),
      zundaNotes=float(data.get("zundaNotes", 0)),
      ankoReserve=float(data.get("ankoReserve", 0)),
      ankoNotes=float(data.get("ankoNotes", 0)),
      azukiNotes=float(data.get("azukiNotes", 0)),
      riceKoku=float(data.get("riceKoku", 1000)),
      goldRyo=float(data.get("goldRyo", 200)),
      silverMonme=float(data.get("silverMonme", 4000)),
      hanSatsu=float(data.get("hanSatsu", 500)),
      hanSatsuCredit=float(data.get("hanSatsuCredit", 1.0)),
      goldSilverRatio=float(data.get("goldSilverRatio", 1.0)),
      dollarNotes=float(data.get("dollarNotes", 0.0)),
      dollarReserves=float(data.get("dollarReserves", 0.0)),
      fxYenPerDollar=float(data.get("fxYenPerDollar", 0.0)),
      monetaryStandard=standard,
      climateIndex=float(data.get("climateIndex", 0.0)),
    )
    return state


@dataclass
class MonthResult:
  harvest: float = 0.0
  riceHarvest: float = 0.0
  edamameHarvest: float = 0.0
  azukiHarvest: float = 0.0
  spoiled: float = 0.0
  taxCollected: float = 0.0
  starvationDeaths: float = 0.0
  notesValueRatio: float = 1.0
  events: list[str] = field(default_factory=list)

  def toDict(self) -> dict[str, Any]:
    return asdict(self)


def monthlySpoilRate(spoilMonths: float) -> float:
  return min(1.0 / max(spoilMonths, 0.01), 1.0)


def climateForMonth(year: int, month: int, eventDisaster: float | None = None) -> tuple[float, float]:
  """Seasonal + famine-decade climate; prefers data/processed/climate_monthly.csv when present."""
  season = [0.1, 0.05, 0.0, -0.05, -0.1, -0.05, 0.0, 0.15, 0.2, 0.1, 0.0, -0.05][month - 1]
  century = -0.2 if 1780 <= year <= 1790 else 0.0  # Tenmei-era cold
  century += -0.15 if 1830 <= year <= 1840 else 0.0  # Tempo-era stress
  century += -0.12 if 1640 <= year <= 1643 else 0.0  # Kan'ei famine window
  century += -0.1 if 1883 <= year <= 1885 else 0.0  # Krakatoa / cool summers
  century += -0.1 if year in (1923, 2011) else 0.0
  proceduralIndex = season + century
  proceduralDisaster = 1.0 + min(proceduralIndex, 0.0)
  if eventDisaster is not None:
    proceduralDisaster = min(proceduralDisaster, eventDisaster)
  proceduralDisaster = max(min(proceduralDisaster, 1.0), 0.2)

  try:
    from src.climate_series import blendClimate, lookupClimateSeries

    climateIndex, disaster, _source = blendClimate(
      proceduralIndex,
      proceduralDisaster,
      lookupClimateSeries(year, month),
      eventDisaster,
    )
    return climateIndex, disaster
  except Exception:
    return proceduralIndex, proceduralDisaster



def cropYield(
  baseYield: float,
  climateIndex: float,
  disasterMultiplier: float,
  climateSensitivity: float,
  coldPenalty: float,
) -> float:
  """Crop-specific yield responding to climateIndex and disasterMultiplier."""
  climateBoost = 1.0 + climateIndex * climateSensitivity
  if climateIndex < 0.0:
    climateBoost += climateIndex * coldPenalty
  factor = disasterMultiplier * max(climateBoost, YIELD_FLOOR)
  return max(baseYield * factor, 0.0)


def advanceMonth(year: int, month: int) -> tuple[int, int]:
  if month >= 12:
    return year + 1, 1
  return year, month + 1


def harvestCrops(economy: EconomyState, disasterMultiplier: float) -> tuple[float, float, float]:
  """Apply per-crop harvest inflows; returns (rice, edamame, azuki) amounts this month."""
  riceHarvest = 0.0
  if economy.month in RICE_HARVEST_MONTHS:
    riceHarvest = cropYield(
      RICE_BASE_YIELD,
      economy.climateIndex,
      disasterMultiplier,
      RICE_CLIMATE_SENSITIVITY,
      RICE_COLD_PENALTY,
    )
    economy.riceKoku += riceHarvest
    economy.foodBuffer += riceHarvest * 0.55
  edamameHarvest, azukiHarvest = harvestBeanCrops(economy, disasterMultiplier)
  return riceHarvest, edamameHarvest, azukiHarvest


def processZunda(economy: EconomyState, ratio: float) -> float:
  take = economy.edamameStock * ratio
  sugarNeed = take * SUGAR_PER_BEAN
  sugarUsed = min(economy.sugarStock, sugarNeed)
  processed = take * PROCESSING_RATIO * (sugarUsed / max(sugarNeed, 1e-9) if sugarNeed else 0.0)
  economy.edamameStock = max(economy.edamameStock - take, 0.0)
  economy.sugarStock -= sugarUsed
  economy.processedZunda += processed
  economy.zundaNotes += processed
  economy.syncRawBeans()
  return processed


def processAnko(economy: EconomyState, ratio: float) -> float:
  take = economy.azukiStock * ratio
  sugarNeed = take * SUGAR_PER_ANKO
  sugarUsed = min(economy.sugarStock, sugarNeed)
  processed = take * ANKO_PROCESSING_RATIO * (sugarUsed / max(sugarNeed, 1e-9) if sugarNeed else 0.0)
  economy.azukiStock = max(economy.azukiStock - take, 0.0)
  economy.sugarStock -= sugarUsed
  economy.ankoReserve += processed
  economy.ankoNotes += processed
  economy.syncRawBeans()
  return processed


def harvestBeanCrops(economy: EconomyState, disasterMultiplier: float) -> tuple[float, float]:
  """Edamame / azuki inflows only (rice is handled separately on edo_metal)."""
  climateIndex = economy.climateIndex
  if economy.month in EDAMAME_HARVEST_MONTHS:
    edamameHarvest = cropYield(
      EDAMAME_BASE_YIELD,
      climateIndex,
      disasterMultiplier,
      EDAMAME_CLIMATE_SENSITIVITY,
      EDAMAME_COLD_PENALTY,
    )
  else:
    edamameHarvest = OFF_SEASON_EDAMAME_TRICKLE * disasterMultiplier
  economy.edamameStock += edamameHarvest

  if economy.month in AZUKI_HARVEST_MONTHS:
    azukiHarvest = cropYield(
      AZUKI_BASE_YIELD,
      climateIndex,
      disasterMultiplier,
      AZUKI_CLIMATE_SENSITIVITY,
      AZUKI_COLD_PENALTY,
    )
  else:
    azukiHarvest = OFF_SEASON_AZUKI_TRICKLE * disasterMultiplier
  economy.azukiStock += azukiHarvest
  economy.syncRawBeans()
  return edamameHarvest, azukiHarvest


def tickSideMarkets(economy: EconomyState, disasterMultiplier: float) -> tuple[float, float]:
  """Bean harvest + light processing for watchable markets under edo_metal."""
  edamameHarvest, azukiHarvest = harvestBeanCrops(economy, disasterMultiplier)
  if economy.sugarStock > 1:
    zTake = min(economy.edamameStock * SIDE_PROCESS_RATIO, SIDE_PROCESS_CAP)
    aTake = min(economy.azukiStock * SIDE_PROCESS_RATIO, SIDE_PROCESS_CAP)
    zSugar = min(economy.sugarStock * 0.02, zTake * SUGAR_PER_BEAN)
    aSugar = min(economy.sugarStock * 0.03, aTake * SUGAR_PER_ANKO)
    economy.processedZunda += zTake * PROCESSING_RATIO * (zSugar / max(zTake * SUGAR_PER_BEAN, 1e-9))
    economy.ankoReserve += aTake * ANKO_PROCESSING_RATIO * (aSugar / max(aTake * SUGAR_PER_ANKO, 1e-9))
    economy.edamameStock = max(economy.edamameStock - zTake, 0.0)
    economy.azukiStock = max(economy.azukiStock - aTake, 0.0)
    economy.sugarStock = max(economy.sugarStock - zSugar - aSugar, 0.0)
    economy.syncRawBeans()
  economy.processedZunda *= 1.0 - monthlySpoilRate(PROCESSED_ZUNDA_SPOIL_MONTHS) * 0.5
  economy.ankoReserve *= 1.0 - monthlySpoilRate(ANKO_SPOIL_MONTHS) * 0.5
  return edamameHarvest, azukiHarvest


def simulateEdoMetalMonth(
  economy: EconomyState,
  policy: EnginePolicy,
  effectiveTaxRate: float,
  reserveRelease: float,
  hanSatsuIssueRatio: float,
  goldSilverTargetRatio: float,
  disasterMultiplier: float,
  crowdHoarding: float,
) -> MonthResult:
  result = MonthResult()
  riceHarvest = 0.0
  if economy.month in RICE_HARVEST_MONTHS:
    riceHarvest = cropYield(
      RICE_BASE_YIELD,
      economy.climateIndex,
      disasterMultiplier,
      RICE_CLIMATE_SENSITIVITY,
      RICE_COLD_PENALTY,
    )
    economy.riceKoku += riceHarvest
    economy.foodBuffer += riceHarvest * 0.55
  economy.foodBuffer += economy.population * MONTHLY_SUBSISTENCE * disasterMultiplier

  edamameHarvest, azukiHarvest = tickSideMarkets(economy, disasterMultiplier)
  result.riceHarvest = riceHarvest
  result.edamameHarvest = edamameHarvest
  result.azukiHarvest = azukiHarvest
  result.harvest = riceHarvest + edamameHarvest + azukiHarvest

  # Gold/silver market drift toward policy target, with noise from disasters.
  ratioGap = goldSilverTargetRatio - economy.goldSilverRatio
  economy.goldSilverRatio += ratioGap * 0.05
  economy.goldSilverRatio *= 0.98 + 0.02 * disasterMultiplier

  # Han-satsu issuance reduces credit.
  issued = economy.riceKoku * hanSatsuIssueRatio * 0.1
  economy.hanSatsu += issued
  if issued > 0:
    economy.hanSatsuCredit = max(economy.hanSatsuCredit - issued * 0.002, 0.1)
  else:
    economy.hanSatsuCredit = min(economy.hanSatsuCredit + 0.001, 1.0)

  taxBase = economy.riceKoku * 0.3 + economy.goldRyo * 2.0 + economy.silverMonme * 0.05
  tax = taxBase * effectiveTaxRate
  economy.riceKoku = max(economy.riceKoku - tax * 0.4, 0.0)
  economy.goldRyo = max(economy.goldRyo - tax * 0.05, 0.0)
  result.taxCollected = tax

  if reserveRelease > 0:
    released = min(economy.riceKoku * 0.1, reserveRelease)
    economy.riceKoku -= released
    economy.foodBuffer += released

  consumption = economy.population * BASE_FOOD_CONSUMPTION * (1.0 + crowdHoarding * 0.3)
  economy.foodBuffer -= consumption
  if economy.foodBuffer < 0:
    deficit = -economy.foodBuffer
    economy.foodBuffer = 0.0
    deaths = min(deficit * 2.0, economy.population * 0.02)
    economy.population = max(economy.population - deaths, POPULATION_FLOOR)
    result.starvationDeaths = deaths

  noteValue = (
    economy.riceKoku * 0.5
    + economy.goldRyo * economy.goldSilverRatio
    + economy.silverMonme * 0.02
    + economy.hanSatsu * economy.hanSatsuCredit * 0.1
  )
  result.notesValueRatio = max(min(noteValue / max(economy.population, 1.0) / 10.0, 2.0), 0.1)
  return result


GOLD_YEN_RATIO_PULL = 0.12
SILVER_TO_GOLD_RATE = 0.004


def simulateGoldYenMonth(
  economy: EconomyState,
  policy: EnginePolicy,
  effectiveTaxRate: float,
  reserveRelease: float,
  goldSilverTargetRatio: float,
  disasterMultiplier: float,
  crowdHoarding: float,
) -> MonthResult:
  """Meiji–Showa gold yen: same harvest as metal, no hansatsu issue, faster gold peg."""
  peg = 1.0 if economy.year < 1932 else float(goldSilverTargetRatio)
  result = simulateEdoMetalMonth(
    economy,
    policy,
    effectiveTaxRate,
    reserveRelease,
    0.0,
    peg,
    disasterMultiplier,
    crowdHoarding,
  )
  ratioGap = peg - economy.goldSilverRatio
  economy.goldSilverRatio += ratioGap * GOLD_YEN_RATIO_PULL
  converted = economy.silverMonme * SILVER_TO_GOLD_RATE
  economy.silverMonme = max(economy.silverMonme - converted, 0.0)
  economy.goldRyo += converted * 0.02
  economy.hanSatsuCredit = min(economy.hanSatsuCredit + 0.002, 1.0)
  return result


def simulateDollarMonth(
  economy: EconomyState,
  policy: EnginePolicy,
  effectiveTaxRate: float,
  reserveRelease: float,
  disasterMultiplier: float,
  crowdHoarding: float,
) -> MonthResult:
  """Real harvest like metal; money is dollar notes/reserves. FX stub, not calibrated CPI."""
  from src.dollar_fx import fxYenPerDollar

  result = MonthResult()
  riceHarvest = 0.0
  if economy.month in RICE_HARVEST_MONTHS:
    riceHarvest = cropYield(
      RICE_BASE_YIELD,
      economy.climateIndex,
      disasterMultiplier,
      RICE_CLIMATE_SENSITIVITY,
      RICE_COLD_PENALTY,
    )
    economy.riceKoku += riceHarvest
    economy.foodBuffer += riceHarvest * 0.55
  economy.foodBuffer += economy.population * MONTHLY_SUBSISTENCE * disasterMultiplier
  edamameHarvest, azukiHarvest = tickSideMarkets(economy, disasterMultiplier)
  result.riceHarvest = riceHarvest
  result.edamameHarvest = edamameHarvest
  result.azukiHarvest = azukiHarvest
  result.harvest = riceHarvest + edamameHarvest + azukiHarvest

  economy.fxYenPerDollar = fxYenPerDollar(economy.year, economy.month)
  if reserveRelease > 0:
    released = min(economy.dollarReserves * 0.2, reserveRelease * 10.0)
    economy.dollarReserves = max(economy.dollarReserves - released, 0.0)
    economy.foodBuffer += released * 0.05
  economy.dollarNotes += policy.investSugarImport * 0.4
  economy.dollarReserves += policy.investSugarImport * 0.15
  tax = economy.dollarNotes * effectiveTaxRate
  economy.dollarNotes = max(economy.dollarNotes - tax, 0.0)
  result.taxCollected = tax
  backing = max(economy.dollarReserves, 1.0)
  result.notesValueRatio = max(min(backing / max(economy.dollarNotes, 1.0), 2.0), 0.05)

  consumption = economy.population * BASE_FOOD_CONSUMPTION * (1.0 + crowdHoarding * 0.3)
  economy.foodBuffer -= consumption
  if economy.foodBuffer < 0:
    deficit = -economy.foodBuffer
    economy.foodBuffer = 0.0
    deaths = min(deficit * 2.0, economy.population * 0.02)
    economy.population = max(economy.population - deaths, POPULATION_FLOOR)
    result.starvationDeaths = deaths
  economy.sugarStock = max(economy.sugarStock + policy.investSugarImport * 0.12 - 1.2, 0.0)
  return result


def simulateCommodityMonth(
  economy: EconomyState,
  policy: EnginePolicy,
  effectiveTaxRate: float,
  reserveRelease: float,
  disasterMultiplier: float,
  crowdHoarding: float,
) -> MonthResult:
  result = MonthResult()
  riceHarvest, edamameHarvest, azukiHarvest = harvestCrops(economy, disasterMultiplier)
  # Commodity food buffer also gets a bean share (was 0.45 of shared harvest).
  economy.foodBuffer += (edamameHarvest + azukiHarvest) * 0.45
  economy.foodBuffer += economy.population * MONTHLY_SUBSISTENCE * disasterMultiplier

  result.riceHarvest = riceHarvest
  result.edamameHarvest = edamameHarvest
  result.azukiHarvest = azukiHarvest
  result.harvest = riceHarvest + edamameHarvest + azukiHarvest

  if economy.monetaryStandard == MonetaryStandard.ZUNDA:
    processZunda(economy, policy.processBeansRatio)
    spoilRate = monthlySpoilRate(PROCESSED_ZUNDA_SPOIL_MONTHS)
    spoiled = economy.processedZunda * spoilRate
    economy.processedZunda -= spoiled
    result.spoiled = spoiled
    reserve = economy.processedZunda
    if reserveRelease > 0:
      released = min(reserve, reserveRelease)
      economy.processedZunda -= released
      economy.foodBuffer += released
      economy.zundaNotes = max(economy.zundaNotes - released * 0.5, 0.0)
    backing = max(economy.processedZunda, 1.0)
    result.notesValueRatio = max(min(backing / max(economy.zundaNotes, 1.0), 2.0), 0.05)
    tax = economy.zundaNotes * effectiveTaxRate
    economy.zundaNotes = max(economy.zundaNotes - tax, 0.0)
  elif economy.monetaryStandard == MonetaryStandard.ANKO:
    processAnko(economy, policy.processBeansRatio)
    spoilRate = monthlySpoilRate(ANKO_SPOIL_MONTHS)
    spoiled = economy.ankoReserve * spoilRate
    economy.ankoReserve -= spoiled
    result.spoiled = spoiled
    if reserveRelease > 0:
      released = min(economy.ankoReserve, reserveRelease)
      economy.ankoReserve -= released
      economy.foodBuffer += released
      economy.ankoNotes = max(economy.ankoNotes - released * 0.5, 0.0)
    backing = max(economy.ankoReserve, 1.0)
    result.notesValueRatio = max(min(backing / max(economy.ankoNotes, 1.0), 2.0), 0.05)
    tax = economy.ankoNotes * effectiveTaxRate
    economy.ankoNotes = max(economy.ankoNotes - tax, 0.0)
  else:
    # Dried azuki standard: warehouse beans back notes; do not cook into anko.
    minted = economy.azukiStock * policy.processBeansRatio * AZUKI_NOTE_MINT_RATIO
    economy.azukiNotes += minted
    if reserveRelease > 0:
      released = min(economy.azukiStock, reserveRelease)
      economy.azukiStock -= released
      economy.foodBuffer += released
      economy.azukiNotes = max(economy.azukiNotes - released * 0.5, 0.0)
    backing = max(economy.azukiStock, 1.0)
    result.notesValueRatio = max(min(backing / max(economy.azukiNotes, 1.0), 2.0), 0.05)
    tax = economy.azukiNotes * effectiveTaxRate
    economy.azukiNotes = max(economy.azukiNotes - tax, 0.0)
    result.spoiled = 0.0
  result.taxCollected = tax

  edamameSpoil = economy.edamameStock * monthlySpoilRate(RAW_BEAN_SPOIL_MONTHS)
  azukiSpoilMonths = (
    DRY_AZUKI_SPOIL_MONTHS
    if economy.monetaryStandard == MonetaryStandard.AZUKI
    else RAW_BEAN_SPOIL_MONTHS
  )
  azukiSpoil = economy.azukiStock * monthlySpoilRate(azukiSpoilMonths)
  economy.edamameStock = max(economy.edamameStock - edamameSpoil, 0.0)
  economy.azukiStock = max(economy.azukiStock - azukiSpoil, 0.0)
  economy.syncRawBeans()
  result.spoiled += edamameSpoil + azukiSpoil

  consumption = economy.population * BASE_FOOD_CONSUMPTION * (1.0 + crowdHoarding * 0.3)
  economy.foodBuffer -= consumption
  if economy.foodBuffer < 0:
    deficit = -economy.foodBuffer
    economy.foodBuffer = 0.0
    deaths = min(deficit * 2.0, economy.population * 0.02)
    economy.population = max(economy.population - deaths, POPULATION_FLOOR)
    result.starvationDeaths = deaths

  # Mild sugar drain / import effect
  economy.sugarStock = max(economy.sugarStock + policy.investSugarImport * 0.1 - 1.0, 0.0)
  # Keep the other sweet paste market alive for price watching.
  if economy.monetaryStandard == MonetaryStandard.ZUNDA:
    economy.ankoReserve = max(economy.ankoReserve + azukiHarvest * 0.05, 0.0)
  elif economy.monetaryStandard == MonetaryStandard.ANKO:
    economy.processedZunda = max(economy.processedZunda + edamameHarvest * 0.05, 0.0)
  else:
    economy.processedZunda = max(economy.processedZunda + edamameHarvest * 0.05, 0.0)
    economy.ankoReserve = max(economy.ankoReserve + azukiHarvest * 0.03, 0.0)
  return result


def simulateMonth(
  economy: EconomyState,
  policy: EnginePolicy,
  effectiveTaxRate: float,
  reserveRelease: float,
  disasterMultiplier: float,
  crowdHoarding: float = 0.0,
  hanSatsuIssueRatio: float = 0.0,
  goldSilverTargetRatio: float = 1.0,
) -> MonthResult:
  if economy.monetaryStandard == MonetaryStandard.EDO_METAL:
    return simulateEdoMetalMonth(
      economy,
      policy,
      effectiveTaxRate,
      reserveRelease,
      hanSatsuIssueRatio,
      goldSilverTargetRatio,
      disasterMultiplier,
      crowdHoarding,
    )
  if economy.monetaryStandard == MonetaryStandard.GOLD_YEN:
    return simulateGoldYenMonth(
      economy,
      policy,
      effectiveTaxRate,
      reserveRelease,
      goldSilverTargetRatio,
      disasterMultiplier,
      crowdHoarding,
    )
  if economy.monetaryStandard == MonetaryStandard.DOLLAR:
    return simulateDollarMonth(
      economy,
      policy,
      effectiveTaxRate,
      reserveRelease,
      disasterMultiplier,
      crowdHoarding,
    )
  return simulateCommodityMonth(
    economy,
    policy,
    effectiveTaxRate,
    reserveRelease,
    disasterMultiplier,
    crowdHoarding,
  )


def reserveBase(economy: EconomyState) -> float:
  if economy.monetaryStandard == MonetaryStandard.ZUNDA:
    return economy.processedZunda
  if economy.monetaryStandard == MonetaryStandard.ANKO:
    return economy.ankoReserve
  if economy.monetaryStandard == MonetaryStandard.AZUKI:
    return economy.azukiStock
  if economy.monetaryStandard == MonetaryStandard.DOLLAR:
    return economy.dollarReserves
  return economy.riceKoku
