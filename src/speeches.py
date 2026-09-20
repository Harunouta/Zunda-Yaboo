"""Public-speech catalog (Wikipedia excerpts) + emit gate for ruler announcements."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

WORKSPACE = Path(__file__).resolve().parents[1]
SPEECHES_ROOT = WORKSPACE / "data" / "events" / "speeches"
CATALOG_PATH = SPEECHES_ROOT / "catalog.yaml"
# Extra sim-facing shards (e.g. catalog_wartime_modern.yaml). Later files override keys.
CATALOG_GLOB = "catalog*.yaml"

# Calm months: low chance of a speech, and only when --llm.
CALM_SPEECH_RATE = 0.06
CALM_SPEECH_BUCKETS = 1000


@dataclass(frozen=True)
class SpeechEntry:
  speechId: str
  yearMonth: str
  eventIds: tuple[str, ...]
  situationKey: str
  publicSpeech: str
  evidence: str = ""
  notes: str = ""


def _catalogPaths() -> list[Path]:
  paths = sorted(SPEECHES_ROOT.glob(CATALOG_GLOB))
  if CATALOG_PATH.exists() and CATALOG_PATH not in paths:
    paths.insert(0, CATALOG_PATH)
  # Prefer base catalog.yaml first, then catalog_*.yaml shards.
  ordered: list[Path] = []
  if CATALOG_PATH.exists():
    ordered.append(CATALOG_PATH)
  for path in paths:
    if path.resolve() != CATALOG_PATH.resolve():
      ordered.append(path)
  return ordered


def _parseCatalogMapping(raw: dict[str, Any], path: Path) -> dict[str, SpeechEntry]:
  catalog: dict[str, SpeechEntry] = {}
  for speechId, entry in raw.items():
    if str(speechId).startswith("#") or not isinstance(entry, dict):
      continue
    speechText = str(entry.get("publicSpeech") or "").strip()
    if not speechText:
      continue
    eventIdsRaw = entry.get("eventIds") or []
    if isinstance(eventIdsRaw, str):
      eventIds = (eventIdsRaw,)
    else:
      eventIds = tuple(str(item) for item in eventIdsRaw)
    catalog[str(speechId)] = SpeechEntry(
      speechId=str(speechId),
      yearMonth=str(entry.get("yearMonth") or ""),
      eventIds=eventIds,
      situationKey=str(entry.get("situationKey") or ""),
      publicSpeech=speechText,
      evidence=str(entry.get("evidence") or ""),
      notes=str(entry.get("notes") or ""),
    )
  return catalog

@lru_cache(maxsize=1)
def loadSpeechCatalog() -> dict[str, SpeechEntry]:
  catalog: dict[str, SpeechEntry] = {}
  for path in _catalogPaths():
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
      raise ValueError(f"speech catalog must be a mapping: {path}")
    catalog.update(_parseCatalogMapping(raw, path))
  return catalog


def clearSpeechCatalogCache() -> None:
  loadSpeechCatalog.cache_clear()


def _indexByYearMonth() -> dict[str, SpeechEntry]:
  byMonth: dict[str, SpeechEntry] = {}
  for entry in loadSpeechCatalog().values():
    if entry.yearMonth and entry.yearMonth not in byMonth:
      byMonth[entry.yearMonth] = entry
  return byMonth


def _indexByEventId() -> dict[str, SpeechEntry]:
  byEvent: dict[str, SpeechEntry] = {}
  for entry in loadSpeechCatalog().values():
    for eventId in entry.eventIds:
      if eventId and eventId not in byEvent:
        byEvent[eventId] = entry
  return byEvent


def lookupSpeech(
  yearMonth: str,
  events: list[str] | tuple[str, ...] | None = None,
) -> SpeechEntry | None:
  """Prefer exact yearMonth, then any overlapping eventId (situation reuse)."""
  catalog = loadSpeechCatalog()
  if not catalog:
    return None
  byMonth = _indexByYearMonth()
  if yearMonth in byMonth:
    return byMonth[yearMonth]
  byEvent = _indexByEventId()
  for eventId in events or []:
    hit = byEvent.get(eventId)
    if hit is not None:
      return hit
  return None


def eventsHaveFxIntervention(eventPayloads: list[Any]) -> bool:
  for payload in eventPayloads:
    strength = float(getattr(payload, "fxInterventionStrength", 0.0) or 0.0)
    direction = str(getattr(payload, "fxInterventionDirection", "") or "").strip()
    if strength > 0.0 and direction:
      return True
  return False


def calmSpeechRoll(yearMonth: str) -> bool:
  """Deterministic calm-month roll so resume stays stable."""
  total = sum(ord(ch) for ch in f"publicSpeech:{yearMonth}")
  return (total % CALM_SPEECH_BUCKETS) / float(CALM_SPEECH_BUCKETS) < CALM_SPEECH_RATE


def shouldEmitPublicSpeech(
  *,
  yearMonth: str,
  events: list[str],
  isAbnormal: bool,
  regimeChange: Any,
  hasFxIntervention: bool,
  useLlm: bool,
  catalogHit: bool,
) -> bool:
  if catalogHit:
    return True
  if regimeChange:
    return True
  if hasFxIntervention:
    return True
  if isAbnormal:
    return True
  if useLlm and calmSpeechRoll(yearMonth):
    return True
  return False


def resolvePublicSpeech(
  *,
  yearMonth: str,
  events: list[str],
  historicalPolicy: bool,
  useLlm: bool,
  isAbnormal: bool,
  regimeChange: Any,
  hasFxIntervention: bool,
  llmPublicSpeech: str = "",
) -> tuple[str, str, str]:
  """Return (publicSpeech, speechSource, speechId).

  speechSource: catalog | llm | none
  Catalog wins whenever a situation matches (historical + free-play similarity).
  """
  hit = lookupSpeech(yearMonth, events)
  catalogHit = hit is not None
  emit = shouldEmitPublicSpeech(
    yearMonth=yearMonth,
    events=events,
    isAbnormal=isAbnormal,
    regimeChange=regimeChange,
    hasFxIntervention=hasFxIntervention,
    useLlm=useLlm,
    catalogHit=catalogHit,
  )
  if not emit:
    return "", "none", ""
  if hit is not None:
    return hit.publicSpeech, "catalog", hit.speechId
  if historicalPolicy:
    return "", "none", ""
  speech = str(llmPublicSpeech or "").strip()
  if useLlm and speech:
    return speech, "llm", ""
  return "", "none", ""
