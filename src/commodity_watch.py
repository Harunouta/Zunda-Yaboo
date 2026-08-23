"""Always-on zunda/anko price watching (both exist since bakufu founding)."""

from dataclasses import dataclass
from typing import Any

from src.events import eventsWarrantPriceBump


BASE_ZUNDA_PRICE = 1.0
BASE_ANKO_PRICE = 1.15
BASE_AZUKI_PRICE = 0.95
RICE_ANCHOR = 1.0
EDAMAME_STOCK_REF = 80.0
AZUKI_STOCK_REF = 70.0
PROCESSED_REF = 200.0
RICE_STOCK_REF = 1000.0


@dataclass
class CommodityWatch:
  zundaPrice: float = BASE_ZUNDA_PRICE
  ankoPrice: float = BASE_ANKO_PRICE
  azukiPrice: float = BASE_AZUKI_PRICE
  ricePrice: float = RICE_ANCHOR
  goldPrice: float = 1.0
  silverPrice: float = 1.0
  zundaVsRice: float = 1.0
  ankoVsRice: float = 1.15
  azukiVsRice: float = 0.95
  zundaVsAnko: float = BASE_ZUNDA_PRICE / BASE_ANKO_PRICE
  dollarPrice: float = 1.0

  def toDict(self) -> dict[str, Any]:
    return {
      "zundaPrice": round(self.zundaPrice, 4),
      "ankoPrice": round(self.ankoPrice, 4),
      "azukiPrice": round(self.azukiPrice, 4),
      "ricePrice": round(self.ricePrice, 4),
      "goldPrice": round(self.goldPrice, 4),
      "silverPrice": round(self.silverPrice, 4),
      "zundaVsRice": round(self.zundaVsRice, 4),
      "ankoVsRice": round(self.ankoVsRice, 4),
      "azukiVsRice": round(self.azukiVsRice, 4),
      "zundaVsAnko": round(self.zundaVsAnko, 4),
      "dollarPrice": round(self.dollarPrice, 4),
    }


def updateCommodityWatch(
  climateIndex: float,
  disasterMultiplier: float,
  sugarStock: float,
  processedZunda: float,
  ankoReserve: float,
  riceKoku: float,
  goldSilverRatio: float,
  crowdHoarding: float,
  events: list[str],
  edamameStock: float = 0.0,
  azukiStock: float = 0.0,
  riceHarvest: float = 0.0,
  edamameHarvest: float = 0.0,
  azukiHarvest: float = 0.0,
  dollarNotes: float = 0.0,
  dollarReserves: float = 0.0,
) -> CommodityWatch:
  """Prices exist under every monetary standard (setting: both since 1603)."""
  # Processed paste scarcity plus raw crop stock / recent yield pressure.
  scarcityZunda = 1.0 / max(processedZunda / PROCESSED_REF + 0.2, 0.2)
  scarcityZunda *= 1.0 / max(edamameStock / EDAMAME_STOCK_REF + 0.25, 0.25) ** 0.35
  scarcityZunda *= 1.0 / max(edamameHarvest / 20.0 + 0.5, 0.5) ** 0.2

  scarcityAnko = 1.0 / max(ankoReserve / PROCESSED_REF + 0.2, 0.2)
  scarcityAnko *= 1.0 / max(azukiStock / AZUKI_STOCK_REF + 0.25, 0.25) ** 0.35
  scarcityAnko *= 1.0 / max(azukiHarvest / 18.0 + 0.5, 0.5) ** 0.2

  sugarFactor = 1.0 + max(0.0, (100.0 - sugarStock) / 200.0)
  climateStress = 1.0 + max(0.0, -climateIndex) * 0.4 + (1.0 - disasterMultiplier) * 0.8
  # Edamame is more climate-sensitive in the overnight crop model.
  zundaClimate = climateStress * (1.0 + max(0.0, -climateIndex) * 0.15)
  azukiClimate = climateStress * (1.0 + max(0.0, -climateIndex) * 0.08)
  hoard = 1.0 + crowdHoarding * 0.25
  eventBump = 1.35 if eventsWarrantPriceBump(events) else 1.0

  ricePrice = RICE_ANCHOR * climateStress * hoard * eventBump
  ricePrice *= 1.0 / max(riceKoku / RICE_STOCK_REF, 0.3) ** 0.15
  ricePrice *= 1.0 / max(riceHarvest / 200.0 + 0.5, 0.5) ** 0.12

  zundaPrice = BASE_ZUNDA_PRICE * scarcityZunda * sugarFactor * zundaClimate * hoard * eventBump
  ankoPrice = BASE_ANKO_PRICE * scarcityAnko * (sugarFactor ** 1.2) * azukiClimate * hoard * eventBump
  scarcityDryAzuki = 1.0 / max(azukiStock / AZUKI_STOCK_REF + 0.25, 0.25)
  scarcityDryAzuki *= 1.0 / max(azukiHarvest / 18.0 + 0.5, 0.5) ** 0.2
  azukiPrice = BASE_AZUKI_PRICE * scarcityDryAzuki * (sugarFactor ** 0.4) * azukiClimate * hoard * eventBump

  dollarPrice = 1.0 * (max(dollarNotes, 1.0) / max(dollarReserves, 1.0))
  dollarPrice *= sugarFactor * hoard * (1.0 + (eventBump - 1.0) * 0.4)

  goldPrice = goldSilverRatio
  silverPrice = 1.0 / max(goldSilverRatio, 0.1)

  return CommodityWatch(
    zundaPrice=zundaPrice,
    ankoPrice=ankoPrice,
    azukiPrice=azukiPrice,
    ricePrice=ricePrice,
    goldPrice=goldPrice,
    silverPrice=silverPrice,
    zundaVsRice=zundaPrice / max(ricePrice, 1e-6),
    ankoVsRice=ankoPrice / max(ricePrice, 1e-6),
    azukiVsRice=azukiPrice / max(ricePrice, 1e-6),
    zundaVsAnko=zundaPrice / max(ankoPrice, 1e-6),
    dollarPrice=dollarPrice,
  )
