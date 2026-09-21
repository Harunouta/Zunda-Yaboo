"""Freedom mode: ruler LLM may switch among a fixed pool of monetary standards."""

from __future__ import annotations

from src.economy import MonetaryStandard, STOCK_SCALE, isYenFxStandard

FREEDOM_STANDARD_VALUES = ("zunda", "anko", "azuki", "edo_metal")
FREEDOM_STANDARDS = frozenset(MonetaryStandard(value) for value in FREEDOM_STANDARD_VALUES)
FREEDOM_COOLDOWN_MONTHS = 12
FREEDOM_PROMPT_MARKER = "FREEDOM_STANDARD_SWITCH"


def isFreedomEligibleStandard(standard: str) -> bool:
  return str(standard or "").strip() in FREEDOM_STANDARD_VALUES


def parseFreedomStandard(raw: object) -> MonetaryStandard | None:
  text = str(raw or "").strip().lower()
  if not text:
    return None
  try:
    candidate = MonetaryStandard(text)
  except ValueError:
    return None
  if candidate not in FREEDOM_STANDARDS:
    return None
  return candidate


def monthsBetween(earlierYm: str, laterYm: str) -> int:
  ey, em = earlierYm.split("-")
  ly, lm = laterYm.split("-")
  return (int(ly) - int(ey)) * 12 + (int(lm) - int(em))


def seedStocksForStandard(economy, wanted: MonetaryStandard) -> None:
  """Raise floors so a mid-run switch does not starve the new regime."""
  economy.processedZunda = max(float(economy.processedZunda or 0.0), 200.0 * STOCK_SCALE)
  economy.ankoReserve = max(float(economy.ankoReserve or 0.0), 180.0 * STOCK_SCALE)
  if wanted == MonetaryStandard.ANKO:
    economy.sugarStock = max(float(economy.sugarStock or 0.0), 450.0 * STOCK_SCALE)
  if wanted == MonetaryStandard.AZUKI:
    economy.azukiStock = max(float(economy.azukiStock or 0.0), 220.0 * STOCK_SCALE)
    economy.azukiNotes = max(float(economy.azukiNotes or 0.0), 80.0 * STOCK_SCALE)
  if wanted == MonetaryStandard.EDO_METAL:
    economy.foodBuffer = max(float(economy.foodBuffer or 0.0), 2500.0 * STOCK_SCALE)
    economy.riceKoku = max(float(economy.riceKoku or 0.0), 1200.0 * STOCK_SCALE)
  if isYenFxStandard(wanted):
    # Freedom pool excludes yen FX; keep defensive floors if ever reused.
    economy.foodBuffer = max(float(economy.foodBuffer or 0.0), 2500.0 * STOCK_SCALE)
    economy.riceKoku = max(float(economy.riceKoku or 0.0), 1200.0 * STOCK_SCALE)


def applyFreedomSwitch(
  economy,
  *,
  requested: MonetaryStandard | None,
  yearMonth: str,
  lastSwitchYm: str | None,
  cooldownMonths: int = FREEDOM_COOLDOWN_MONTHS,
) -> tuple[str | None, str | None]:
  """Apply LLM-requested switch. Returns (regimeChangeLabel, newLastSwitchYm)."""
  if requested is None:
    return None, lastSwitchYm
  if requested not in FREEDOM_STANDARDS:
    return None, lastSwitchYm
  previous = economy.monetaryStandard
  if previous not in FREEDOM_STANDARDS:
    return None, lastSwitchYm
  if requested == previous:
    return None, lastSwitchYm
  if lastSwitchYm:
    elapsed = monthsBetween(lastSwitchYm, yearMonth)
    if elapsed < cooldownMonths:
      return None, lastSwitchYm
  economy.monetaryStandard = requested
  seedStocksForStandard(economy, requested)
  label = f"freedom:{previous.value}->{requested.value}"
  return label, yearMonth


def freedomPromptAddon(currentStandard: str) -> str:
  pool = "|".join(FREEDOM_STANDARD_VALUES)
  return (
    f"{FREEDOM_PROMPT_MARKER}: optional top-level nextStandard "
    f"(one of {pool}; empty or omit = keep {currentStandard}). "
    "Switch only when stuck or changing course — rarely, not every month. "
    "No automatic rule thresholds; you decide."
  )
