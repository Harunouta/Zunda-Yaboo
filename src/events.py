"""Monthly historical events — loaded from data/events/ (CSV + YAML).

Public API stays stable for monthly_engine / opinion_agents:
  getEventsForMonth, getEventPayload, isAbnormalMonth,
  buildLeaderPrompt, buildCrowdPrompt, EVENT_TABLE, MONTHLY_EVENTS
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

WORKSPACE = Path(__file__).resolve().parents[1]
EVENTS_ROOT = WORKSPACE / "data" / "events"

DISASTER_LEADER_THRESHOLD = 0.7
VALID_SCOPES = frozenset({"japan", "japan_info", "world"})
FAMINE_EVENT_PREFIXES = ("tenmei_famine", "tenpo_famine")
NAMED_PRICE_BUMP_EVENTS = frozenset({"perry_arrival", "war_end"})
# Catalog heuristics: smaller disasterOverride = worse harvest; used by prices + dry-run policy.
PRICE_BUMP_DISASTER_MAX = 0.55
PRICE_BUMP_EPIDEMIC_MIN = 0.25
DISASTER_RELIEF_DISASTER_MAX = 0.55
EPIDEMIC_POLICY_MIN = 0.25


def eventIdMatchesPrefix(eventId: str, prefix: str) -> bool:
  return eventId == prefix or eventId.startswith(f"{prefix}_")


def eventsIncludeAnyPrefix(events: list[str] | tuple[str, ...] | set[str], prefixes: tuple[str, ...]) -> bool:
  return any(
    eventIdMatchesPrefix(eventId, prefix)
    for eventId in events
    for prefix in prefixes
  )


@dataclass
class EventPayload:
  eventId: str
  promptForLeader: str
  promptForOpinionLeader: str
  disasterOverride: float | None = None
  worldEffect: str | None = None
  populationShock: float = 0.0
  cropLossExtra: float = 0.0
  epidemicSeverity: float = 0.0
  scope: str = "japan"
  notes: str = ""
  targetArea: str = "ALL"
  landPollution: float = 0.0
  infraDamage: float = 0.0
  laborDrain: float = 0.0
  socialUnrest: float = 0.0
  stockSpoilage: float = 0.0
  govDemand: float = 0.0
  importCostShock: float = 0.0
  exportDrain: float = 0.0
  fiatTrustShock: float = 0.0


def _optionalFloat(value: Any) -> float | None:
  if value is None or value == "":
    return None
  return float(value)


def _floatOrZero(value: Any) -> float:
  if value is None or value == "":
    return 0.0
  return float(value)


def inferTargetArea(eventId: str, notes: str, explicit: str | None) -> str:
  if explicit:
    return str(explicit).strip() or "ALL"
  blob = f"{eventId} {notes}".lower()
  if any(token in blob for token in ("asama", "浅間", "tohoku", "東北", "三陸")):
    return "tohoku_rim"
  if any(token in blob for token in ("sakurajima", "桜島", "unzen", "島原", "kyushu", "九州")):
    return "osaka_hub"
  if any(token in blob for token in ("hoei_fuji", "fuji", "富士", "edo", "kanto", "関東", "江戸")):
    return "edo_core"
  return "ALL"


PHYSICAL_DISASTER_MARKERS = (
  "噴火",
  "eruption",
  "fuji",
  "asama",
  "unzen",
  "sakurajima",
  "volcano",
  "地震",
  "earthquake",
  "津波",
  "tsunami",
  "洪水",
  "flood",
  "台風",
  "typhoon",
  "水害",
  "火事",
  "大火",
  "fire",
)


def _legacyMediatorFields(entry: dict, eventId: str, notes: str) -> dict[str, float | str]:
  disaster = _optionalFloat(entry.get("disasterOverride"))
  blob = f"{eventId} {notes}".lower()
  isPhysical = any(marker.lower() in blob for marker in PHYSICAL_DISASTER_MARKERS)
  landPollution = _floatOrZero(entry.get("landPollution"))
  infraDamage = _floatOrZero(entry.get("infraDamage"))
  if landPollution <= 0.0 and disaster is not None and isPhysical:
    landPollution = min(1.0, (1.0 - disaster) * 0.28)
  if infraDamage <= 0.0 and disaster is not None and isPhysical:
    infraDamage = min(1.0, (1.0 - disaster) * 0.32)
  laborDrain = _floatOrZero(entry.get("laborDrain")) or min(0.25, _floatOrZero(entry.get("populationShock")) * 1.0)
  socialUnrest = _floatOrZero(entry.get("socialUnrest")) or min(1.0, _floatOrZero(entry.get("epidemicSeverity")) * 0.8)
  stockSpoilage = _floatOrZero(entry.get("stockSpoilage"))
  if stockSpoilage <= 0.0:
    stockSpoilage = min(0.22, _floatOrZero(entry.get("cropLossExtra")) * 0.4)
  worldEffect = str(entry.get("worldEffect") or "")
  importCostShock = _floatOrZero(entry.get("importCostShock"))
  exportDrain = _floatOrZero(entry.get("exportDrain"))
  fiatTrustShock = _floatOrZero(entry.get("fiatTrustShock"))
  govDemand = _floatOrZero(entry.get("govDemand"))
  if worldEffect in {"sugar_spike", "oil_spike", "chip_spike"} and importCostShock <= 0.0:
    importCostShock = 0.12 if worldEffect == "oil_spike" else 0.08
  if worldEffect == "gold_outflow" and exportDrain <= 0.0:
    exportDrain = 0.1
  if worldEffect in {"hyperinflation", "han_satsu_crisis"} and fiatTrustShock <= 0.0:
    fiatTrustShock = 0.15 if worldEffect == "hyperinflation" else 0.12
  return {
    "targetArea": inferTargetArea(eventId, notes, entry.get("targetArea") or entry.get("target_area")),
    "landPollution": landPollution,
    "infraDamage": infraDamage,
    "laborDrain": laborDrain,
    "socialUnrest": socialUnrest,
    "stockSpoilage": stockSpoilage,
    "govDemand": govDemand,
    "importCostShock": importCostShock,
    "exportDrain": exportDrain,
    "fiatTrustShock": fiatTrustShock,
  }


def _loadCatalogFile(path: Path) -> dict[str, EventPayload]:
  if not path.exists():
    return {}
  raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
  if not isinstance(raw, dict):
    raise ValueError(f"catalog must be a mapping: {path}")
  catalog: dict[str, EventPayload] = {}
  for eventId, entry in raw.items():
    if not isinstance(entry, dict):
      raise ValueError(f"catalog entry must be object: {eventId} in {path}")
    scope = str(entry.get("scope") or "japan")
    if scope not in VALID_SCOPES:
      raise ValueError(f"invalid scope {scope!r} for {eventId} in {path}")
    notes = str(entry.get("notes") or "")
    mediators = _legacyMediatorFields(entry, str(eventId), notes)
    catalog[str(eventId)] = EventPayload(
      eventId=str(eventId),
      promptForLeader=str(entry.get("promptForLeader") or ""),
      promptForOpinionLeader=str(entry.get("promptForOpinionLeader") or ""),
      disasterOverride=_optionalFloat(entry.get("disasterOverride")),
      worldEffect=(str(entry["worldEffect"]) if entry.get("worldEffect") else None),
      populationShock=_floatOrZero(entry.get("populationShock")),
      cropLossExtra=_floatOrZero(entry.get("cropLossExtra")),
      epidemicSeverity=_floatOrZero(entry.get("epidemicSeverity")),
      scope=scope,
      notes=notes,
      targetArea=str(mediators["targetArea"]),
      landPollution=float(mediators["landPollution"]),
      infraDamage=float(mediators["infraDamage"]),
      laborDrain=float(mediators["laborDrain"]),
      socialUnrest=float(mediators["socialUnrest"]),
      stockSpoilage=float(mediators["stockSpoilage"]),
      govDemand=float(mediators["govDemand"]),
      importCostShock=float(mediators["importCostShock"]),
      exportDrain=float(mediators["exportDrain"]),
      fiatTrustShock=float(mediators["fiatTrustShock"]),
    )
  return catalog


def _loadTimelineFile(path: Path) -> dict[str, list[str]]:
  if not path.exists():
    return {}
  monthly: dict[str, list[str]] = {}
  with path.open(encoding="utf-8", newline="") as handle:
    # Allow # comment lines in CSV files.
    filtered = (line for line in handle if line.strip() and not line.lstrip().startswith("#"))
    reader = csv.DictReader(filtered)
    for row in reader:
      yearMonth = str(row.get("yearMonth") or "").strip()
      eventId = str(row.get("eventId") or "").strip()
      if not yearMonth or not eventId:
        continue
      bucket = monthly.setdefault(yearMonth, [])
      if eventId not in bucket:
        bucket.append(eventId)
  return monthly


def _mergeMonthly(*parts: dict[str, list[str]]) -> dict[str, list[str]]:
  merged: dict[str, list[str]] = {}
  for part in parts:
    for yearMonth, eventIds in part.items():
      bucket = merged.setdefault(yearMonth, [])
      for eventId in eventIds:
        if eventId not in bucket:
          bucket.append(eventId)
  return merged


@lru_cache(maxsize=1)
def _loadEventData() -> tuple[dict[str, list[str]], dict[str, EventPayload]]:
  japanCatalog = _loadCatalogFile(EVENTS_ROOT / "japan" / "catalog.yaml")
  worldCatalog = _loadCatalogFile(EVENTS_ROOT / "world" / "catalog.yaml")
  catalog = {**worldCatalog, **japanCatalog}

  japanTimeline = _loadTimelineFile(EVENTS_ROOT / "japan" / "timeline.csv")
  worldTimeline = _loadTimelineFile(EVENTS_ROOT / "world" / "timeline.csv")
  bridgeTimeline = _loadTimelineFile(EVENTS_ROOT / "bridges" / "japan_from_world.csv")
  monthly = _mergeMonthly(japanTimeline, worldTimeline, bridgeTimeline)

  missing = sorted({
    eventId
    for eventIds in monthly.values()
    for eventId in eventIds
    if eventId not in catalog
  })
  if missing:
    raise ValueError(
      "timeline references unknown eventId(s) missing from catalog.yaml: "
      + ", ".join(missing)
    )
  return monthly, catalog


def reloadEventData() -> None:
  """Clear cache after editing CSV/YAML (tests / interactive)."""
  _loadEventData.cache_clear()


def _monthly() -> dict[str, list[str]]:
  return _loadEventData()[0]


def _catalog() -> dict[str, EventPayload]:
  return _loadEventData()[1]


# Lazy module-level aliases (recomputed on each access via functions preferred).
# Kept for callers that import EVENT_TABLE / MONTHLY_EVENTS by name.
class _LazyEventTable(dict):
  def __getitem__(self, key: str) -> EventPayload:
    return _catalog()[key]

  def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
    return _catalog().get(key, default)

  def __contains__(self, key: object) -> bool:
    return key in _catalog()

  def keys(self):  # type: ignore[override]
    return _catalog().keys()

  def items(self):  # type: ignore[override]
    return _catalog().items()

  def values(self):  # type: ignore[override]
    return _catalog().values()

  def __iter__(self):
    return iter(_catalog())

  def __len__(self) -> int:
    return len(_catalog())


class _LazyMonthly(dict):
  def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
    return _monthly().get(key, default)

  def __getitem__(self, key: str) -> list[str]:
    return _monthly()[key]

  def __contains__(self, key: object) -> bool:
    return key in _monthly()

  def items(self):  # type: ignore[override]
    return _monthly().items()

  def keys(self):  # type: ignore[override]
    return _monthly().keys()

  def __iter__(self):
    return iter(_monthly())

  def __len__(self) -> int:
    return len(_monthly())


EVENT_TABLE = _LazyEventTable()
MONTHLY_EVENTS = _LazyMonthly()


def getEventsForMonth(yearMonth: str) -> list[str]:
  return list(_monthly().get(yearMonth, []))


def getEventPayload(eventId: str) -> EventPayload | None:
  return _catalog().get(eventId)


def isAbnormalMonth(events: list[str], disasterMultiplier: float) -> bool:
  """True when historical events fire or climate disaster is severe enough for opinion leaders."""
  if events:
    return True
  return disasterMultiplier < DISASTER_LEADER_THRESHOLD


def eventsWarrantPriceBump(events: list[str]) -> bool:
  """Rice / paste prices jump on famine-class or severe catalog shocks (all monetary standards)."""
  if eventsIncludeAnyPrefix(events, FAMINE_EVENT_PREFIXES):
    return True
  if any(eventId in NAMED_PRICE_BUMP_EVENTS for eventId in events):
    return True
  for eventId in events:
    payload = getEventPayload(eventId)
    if payload is None:
      continue
    if payload.disasterOverride is not None and payload.disasterOverride < PRICE_BUMP_DISASTER_MAX:
      return True
    if payload.epidemicSeverity >= PRICE_BUMP_EPIDEMIC_MIN:
      return True
  return False


def eventsWarrantDisasterRelief(events: list[str]) -> bool:
  if eventsIncludeAnyPrefix(events, FAMINE_EVENT_PREFIXES):
    return True
  for eventId in events:
    payload = getEventPayload(eventId)
    if payload is None:
      continue
    if payload.disasterOverride is not None and payload.disasterOverride < DISASTER_RELIEF_DISASTER_MAX:
      return True
  return False


def eventsWarrantEpidemicPolicy(events: list[str]) -> bool:
  for eventId in events:
    payload = getEventPayload(eventId)
    if payload is not None and payload.epidemicSeverity >= EPIDEMIC_POLICY_MIN:
      return True
  return False


def buildLeaderPrompt(
  events: list[str],
  yearMonth: str,
  standard: str,
  policyHand: list | None = None,
  agriBrief: str = "",
) -> str:
  prompts = [
    getEventPayload(event).promptForLeader
    for event in events
    if getEventPayload(event)
  ]
  base = (
    f"Month {yearMonth}. Edo-bakufu continuity / modern Japan. Monetary standard={standard}. "
    "azuki=dried beans backing (ankomon); anko=paste backing. "
    "Output law+policy JSON. "
    "law.decree は日本語で短く、読む人が笑えるか緊張が伝わる一文にせよ。"
    "任意で top-level rulerReason（日本語1文：なぜその布告か）を付けよ。"
  )
  if not prompts:
    basePrompt = f"{base} Normal governance month — 定例でも退屈な定型文は避け、物価・備蓄・噂のどれかに触れよ。"
  else:
    basePrompt = f"{base} " + " / ".join(prompts)
  try:
    from src.policies import formatPoliciesForLeader

    extra = formatPoliciesForLeader(yearMonth, hand=policyHand)
    if extra:
      basePrompt = f"{basePrompt} {extra}"
  except Exception:
    pass
  if agriBrief:
    basePrompt = f"{basePrompt} Field reports: {agriBrief}"
  return basePrompt


def buildCrowdPrompt(
  events: list[str],
  yearMonth: str,
  foodPerCapita: float,
  legitimacy: float,
  decree: str = "",
  policySummary: str = "",
  agriRumors: str = "",
) -> str:
  prompts = [
    getEventPayload(event).promptForOpinionLeader
    for event in events
    if getEventPayload(event)
  ]
  status = (
    f"Month {yearMonth}. foodPerCapita={foodPerCapita:.4f}, legitimacy={legitimacy:.3f}. "
    f"decree={decree or 'なし'}. policy={policySummary or 'なし'}. "
    "Output JSON: rumor, anger(0-1), hoarding(0-1), riotRisk(0-1), moodText, "
    "crowdMoodDetail, eventReaction. "
    "rumor と moodText は具体的な日本語。抽象的な『不安』だけの文は禁止。"
  )
  if agriRumors:
    status += f" Field: {agriRumors}"
  if prompts:
    return status + " Context: " + " / ".join(prompts)
  return status + " Ordinary month — 茶屋・市・蔵のうち一つを舞台にした噂を作れ。"
