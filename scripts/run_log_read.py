"""Read monthly JSONL for the local HTML viewer. Does not call the sim engine."""

from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import importlib.util

_playSpec = importlib.util.spec_from_file_location("play_run", ROOT / "scripts" / "play_run.py")
_playMod = importlib.util.module_from_spec(_playSpec)
assert _playSpec.loader is not None
_playSpec.loader.exec_module(_playMod)
PRESETS = _playMod.PRESETS

RUNS_DIR = ROOT / "logs" / "runs"
COMPARE_DIR = ROOT / "logs" / "compare_packs"
INDEX_PREFIX = ".viewer_index_"
NOISE_EVENT_IDS = frozenset({"riot_risk", "region_simulated"})
MAX_CHART_MARKERS = 40
MAJOR_EVENT_NEEDLES = (
  "famine",
  "flood",
  "earthquake",
  "eruption",
  "volcano",
  "perry",
  "war_",
  "_war",
  "cholera",
  "covid",
  "tenmei",
  "tenpo",
  "hoei",
  "tsunami",
  "typhoon",
  "kanto",
  "tohoku",
  "sakuradamon",
  "meiji_restoration",
  "taisei_hokan",
  "opium",
  "depression",
  "shogunate_starts",
  "hanshin",
  "atomic",
  "ww2",
  "influenza",
  "pandemic",
)
MAJOR_NOTE_NEEDLES = (
  "飢饉",
  "噴火",
  "地震",
  "津波",
  "黒船",
  "条約",
  "維新",
  "大戦",
  "戦争",
  "洪水",
  "台風",
  "コレラ",
  "疫病",
  "震災",
  "恐慌",
  "開府",
  "原爆",
  "空襲",
  "一揆",
  "開国",
)
BLURB_MAX_CHARS = 80
STEM_PATTERN = "^[A-Za-z0-9._-]+$"
INDEX_VERSION = 3
POP_SWING_RATIO = 0.008
FOOD_SWING_RATIO = 0.12
FIDELITY_SWING = 0.04
RICE_SWING_RATIO = 0.15
MAX_IMPORT_BYTES = 80 * 1024 * 1024
ALLOWED_ZIP_MEMBERS = frozenset(
  {"monthly.jsonl", "launch.json", "life_recap.json", "life_recap.md"}
)
ZIP_MEMBER_ALIASES = {
  "monthly.jsonl": "monthly.jsonl",
  "monthly.jsonl": "monthly.jsonl",
  "launch.json": "launch.json",
  "launch.json": "launch.json",
  "life_recap.json": "life_recap.json",
  "life_recap.json": "life_recap.json",
  "life_recap.md": "life_recap.md",
  "life_recap.md": "life_recap.md",
}
MAX_COMPARE_RUNS = 6


def _safeStem(stem: str) -> str:
  if not stem or "/" in stem or "\\" in stem or ".." in stem:
    raise ValueError("invalid stem")
  if not re.match(STEM_PATTERN, stem):
    raise ValueError("invalid stem")
  return stem


def resolveRunPath(stem: str) -> Path:
  stem = _safeStem(stem)
  runsRoot = RUNS_DIR.resolve()
  folderPath = (RUNS_DIR / stem / "monthly.jsonl").resolve()
  flatPath = (RUNS_DIR / f"{stem}.jsonl").resolve()
  for path in (folderPath, flatPath):
    if not str(path).startswith(str(runsRoot)):
      raise ValueError("path outside logs/runs")
    if path.is_file():
      return path
  compareRoot = COMPARE_DIR.resolve()
  COMPARE_DIR.mkdir(parents=True, exist_ok=True)
  comparePath = (COMPARE_DIR / stem / "monthly.jsonl").resolve()
  if str(comparePath).startswith(str(compareRoot)) and comparePath.is_file():
    return comparePath
  raise FileNotFoundError(stem)


def listRuns() -> list[dict]:
  RUNS_DIR.mkdir(parents=True, exist_ok=True)
  out: list[dict] = []
  seen: set[str] = set()
  for monthly in sorted(RUNS_DIR.glob("*/monthly.jsonl")):
    stem = monthly.parent.name
    if stem.startswith("."):
      continue
    seen.add(stem)
    out.append(_runCard(stem, monthly, "folder"))
  for path in sorted(RUNS_DIR.glob("*.jsonl")):
    if path.name.startswith(".") or path.stem in seen:
      continue
    out.append(_runCard(path.stem, path, "file"))
  out.sort(key=lambda item: item["mtime"], reverse=True)
  return out


def _peekYearMonth(line: str) -> str:
  try:
    return str(json.loads(line).get("yearMonth") or "")
  except json.JSONDecodeError:
    return ""


def _lastNonemptyLine(logPath: Path) -> str:
  with logPath.open("rb") as handle:
    handle.seek(0, 2)
    size = handle.tell()
    if size <= 0:
      return ""
    data = b""
    pos = size
    while pos > 0:
      step = min(8192, pos)
      pos -= step
      handle.seek(pos)
      data = handle.read(step) + data
      if data.count(b"\n") >= 2 or pos == 0:
        break
  text = data.decode("utf-8", errors="replace").strip("\n")
  if not text:
    return ""
  return text.split("\n")[-1]


def _yearRange(logPath: Path) -> tuple[str, str, int]:
  cached = indexPathFor(logPath)
  stat = logPath.stat()
  if cached.is_file():
    try:
      payload = json.loads(cached.read_text(encoding="utf-8"))
      months = payload.get("months") or []
      if (
        payload.get("version") == INDEX_VERSION
        and payload.get("size") == stat.st_size
        and payload.get("mtimeNs") == stat.st_mtime_ns
        and months
      ):
        return (
          str(months[0].get("yearMonth") or ""),
          str(months[-1].get("yearMonth") or ""),
          len(months),
        )
    except (json.JSONDecodeError, OSError, TypeError):
      pass
  first = ""
  with logPath.open("r", encoding="utf-8") as handle:
    for line in handle:
      if line.strip():
        first = _peekYearMonth(line)
        break
  lastYm = _peekYearMonth(_lastNonemptyLine(logPath))
  return first, lastYm, 0


def _runCard(stem: str, logPath: Path, kind: str) -> dict:
  stat = logPath.stat()
  firstYm, lastYm, monthCount = _yearRange(logPath)
  launch: dict = {}
  launchPath = RUNS_DIR / stem / "launch.json"
  if launchPath.is_file():
    try:
      raw = json.loads(launchPath.read_text(encoding="utf-8"))
      if isinstance(raw, dict):
        launch = {
          "standard": raw.get("standard"),
          "start": raw.get("start"),
          "end": raw.get("end"),
          "noLlm": raw.get("noLlm"),
        }
    except (json.JSONDecodeError, OSError):
      launch = {}
  recapJson = logPath.with_name("life_recap.json")
  recapMd = logPath.with_name("life_recap.md")
  return {
    "stem": stem,
    "name": f"{stem}/monthly.jsonl" if kind == "folder" else logPath.name,
    "kind": kind,
    "presets": presetNamesForStem(stem),
    "sizeBytes": stat.st_size,
    "mtime": int(stat.st_mtime),
    "firstYearMonth": firstYm,
    "lastYearMonth": lastYm,
    "monthCount": monthCount,
    "standard": launch.get("standard"),
    "span": launch.get("start") and launch.get("end") and f"{launch.get('start')}..{launch.get('end')}" or "",
    "noLlm": launch.get("noLlm"),
    "hasRecap": bool((recapJson and recapJson.is_file()) or (recapMd and recapMd.is_file())),
  }


def presetNamesForStem(stem: str) -> list[str]:
  names: list[str] = []
  for name, path in PRESETS.items():
    if path.stem == stem:
      names.append(name)
  return names


def indexPathFor(logPath: Path) -> Path:
  label = logPath.parent.name if logPath.name == "monthly.jsonl" else logPath.stem
  return RUNS_DIR / f"{INDEX_PREFIX}{label}.json"


def _blurbFromRow(row: dict) -> str:
  notes = row.get("eventNotes") or []
  if notes:
    text = str(notes[0]).strip()
    if len(text) > BLURB_MAX_CHARS:
      return text[:BLURB_MAX_CHARS] + "…"
    return text
  crowd = row.get("crowd") or {}
  behavior = row.get("behavior") or {}
  law = row.get("law") or {}
  speech = str(behavior.get("mascotSpeech") or crowd.get("mascotSpeech") or "").strip()
  decree = str(law.get("decree") or "").strip()
  text = speech or decree
  if len(text) > BLURB_MAX_CHARS:
    return text[:BLURB_MAX_CHARS] + "…"
  return text


def _visibleEvents(row: dict) -> list[str]:
  notes = row.get("eventNotes")
  if isinstance(notes, list) and notes:
    return [
      str(item)
      for item in notes
      if str(item) not in NOISE_EVENT_IDS
      and not any(str(item).startswith(f"{noise}:") for noise in NOISE_EVENT_IDS)
    ]
  return [str(item) for item in (row.get("events") or []) if item not in NOISE_EVENT_IDS]


def _rowMetrics(row: dict) -> dict:
  macro = row.get("macro") or {}
  prices = row.get("prices") or {}
  ppp = row.get("purchasingPower") or {}
  fidelity = row.get("historicalFidelity") or row.get("historicalFidelity") or {}
  return {
    "population": float(macro.get("population") or 0.0),
    "foodYen": float(ppp.get("foodYenPerCapita") or ppp.get("foodYenPerCapita") or 0.0),
    "fidelity": float(fidelity.get("score") or 0.0),
    "ricePrice": float(prices.get("ricePrice") or 0.0),
    "standard": str(row.get("monetaryStandard") or ""),
  }


def _relJump(current: float, previous: float, ratio: float) -> bool:
  if previous <= 0:
    return False
  return abs(current - previous) / previous >= ratio


def _bigChange(current: dict, previous: dict | None, hasEvents: bool, regimeChange: bool) -> bool:
  if hasEvents or regimeChange:
    return True
  if previous is None:
    return False
  if current["standard"] and previous["standard"] and current["standard"] != previous["standard"]:
    return True
  return (
    _relJump(current["population"], previous["population"], POP_SWING_RATIO)
    or _relJump(current["foodYen"], previous["foodYen"], FOOD_SWING_RATIO)
    or abs(current["fidelity"] - previous["fidelity"]) >= FIDELITY_SWING
    or _relJump(current["ricePrice"], previous["ricePrice"], RICE_SWING_RATIO)
  )


def buildIndex(logPath: Path) -> dict:
  months: list[dict] = []
  previous: dict | None = None
  with logPath.open("r", encoding="utf-8") as handle:
    while True:
      offset = handle.tell()
      line = handle.readline()
      if line == "":
        break
      if not line.strip():
        continue
      row = json.loads(line)
      yearMonth = str(row.get("yearMonth") or "")
      events = _visibleEvents(row)
      speech = str(
        (row.get("behavior") or {}).get("mascotSpeech")
        or (row.get("crowd") or {}).get("mascotSpeech")
        or ""
      ).strip()
      metrics = _rowMetrics(row)
      bigChange = _bigChange(
        metrics,
        previous,
        bool(events),
        bool(row.get("regimeChange")),
      )
      months.append(
        {
          "yearMonth": yearMonth,
          "offset": offset,
          "eventCount": len(events),
          "events": events,
          "hasSpeech": bool(speech),
          "blurb": _blurbFromRow(row),
          "bigChange": bigChange,
          "population": metrics["population"],
        }
      )
      previous = metrics
  payload = {
    "version": INDEX_VERSION,
    "stem": logPath.stem,
    "size": logPath.stat().st_size,
    "mtimeNs": logPath.stat().st_mtime_ns,
    "months": months,
  }
  outPath = indexPathFor(logPath)
  outPath.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
  return payload


def loadIndex(logPath: Path) -> dict:
  cached = indexPathFor(logPath)
  stat = logPath.stat()
  if cached.is_file():
    try:
      payload = json.loads(cached.read_text(encoding="utf-8"))
      if (
        payload.get("version") == INDEX_VERSION
        and payload.get("size") == stat.st_size
        and payload.get("mtimeNs") == stat.st_mtime_ns
      ):
        return payload
    except (json.JSONDecodeError, OSError):
      pass
  return buildIndex(logPath)


def listMonths(
  stem: str,
  fromYm: str = "",
  toYm: str = "",
  onlyEvents: bool = False,
  onlyBigChanges: bool = False,
  onlySpeech: bool = False,
) -> list[dict]:
  logPath = resolveRunPath(stem)
  index = loadIndex(logPath)
  rows: list[dict] = []
  for item in index.get("months") or []:
    yearMonth = str(item.get("yearMonth") or "")
    if fromYm and yearMonth < fromYm:
      continue
    if toYm and yearMonth > toYm:
      continue
    eventCount = int(item.get("eventCount") or 0)
    bigChange = bool(item.get("bigChange"))
    if onlyEvents and eventCount <= 0:
      continue
    if onlyBigChanges and not bigChange:
      continue
    if onlySpeech and not item.get("hasSpeech"):
      continue
    rows.append(
      {
        "yearMonth": yearMonth,
        "eventCount": eventCount,
        "events": item.get("events") or [],
        "hasSpeech": bool(item.get("hasSpeech")),
        "blurb": item.get("blurb") or "",
        "bigChange": bigChange,
        "population": item.get("population"),
      }
    )
  return rows


def _splitEventRef(raw: str) -> tuple[str, str]:
  text = str(raw or "").strip()
  if ": " in text:
    eventId, note = text.split(": ", 1)
    return eventId.strip(), note.strip()
  return text, ""


def _japaneseEventName(eventId: str, packedNote: str = "") -> str:
  if packedNote:
    return packedNote
  from src.events import EVENT_TABLE

  payload = EVENT_TABLE.get(eventId)
  if payload is None:
    return eventId
  notes = str(getattr(payload, "notes", "") or "").strip()
  if notes:
    return notes.splitlines()[0][:80]
  leader = str(getattr(payload, "promptForLeader", "") or "").strip()
  if leader:
    parts = [part.strip() for part in leader.split("。") if part.strip()]
    first = parts[0] if parts else leader
    if len(first) < 16 and len(parts) > 1:
      first = f"{parts[0]}。{parts[1]}"
    return first[:80] + ("…" if len(first) > 80 else "")
  return eventId


def _eventWeight(eventId: str) -> float:
  from src.events import EVENT_TABLE

  payload = EVENT_TABLE.get(eventId)
  weight = 0.0
  lowered = eventId.lower()
  if any(needle in lowered for needle in MAJOR_EVENT_NEEDLES):
    weight += 1.5
  if any(
    token in lowered
    for token in ("perry", "meiji_restoration", "shogunate_starts", "sakuradamon", "covid")
  ):
    weight += 4.0
  if payload is None:
    return weight
  disaster = getattr(payload, "disasterOverride", None)
  if disaster is not None:
    weight += max(0.0, 1.0 - float(disaster)) * 3.0
  weight += abs(float(getattr(payload, "populationShock", 0.0) or 0.0)) * 80.0
  weight += abs(float(getattr(payload, "cropLossExtra", 0.0) or 0.0))
  weight += float(getattr(payload, "epidemicSeverity", 0.0) or 0.0) * 2.0
  return weight


def _isMajorEvent(eventId: str, nameJa: str) -> bool:
  blob = f"{eventId} {nameJa}".lower()
  if any(needle in blob for needle in MAJOR_EVENT_NEEDLES):
    return True
  return any(needle in nameJa for needle in MAJOR_NOTE_NEEDLES)


def chartMarkersFromRows(rows: list[dict]) -> list[dict]:
  scored: list[dict] = []
  for row in rows:
    yearMonth = str(row.get("yearMonth") or "")
    year = int(yearMonth[:4]) if yearMonth[:4].isdigit() else 0
    best: dict | None = None
    for label in row.get("labels") or []:
      eventId = str(label.get("id") or "")
      nameJa = str(label.get("nameJa") or eventId)
      if not _isMajorEvent(eventId, nameJa):
        continue
      weight = _eventWeight(eventId)
      candidate = {
        "year": year,
        "yearMonth": yearMonth,
        "eventId": eventId,
        "nameJa": nameJa,
        "weight": weight,
      }
      if best is None or weight > best["weight"]:
        best = candidate
    if best:
      scored.append(best)
  scored.sort(key=lambda item: (-float(item["weight"]), str(item["yearMonth"])))
  byYear: dict[int, dict] = {}
  for item in scored:
    year = int(item["year"])
    if year not in byYear:
      byYear[year] = item
    if len(byYear) >= MAX_CHART_MARKERS:
      break
  return [byYear[year] for year in sorted(byYear)]


def listEventLog(stem: str) -> list[dict]:
  logPath = resolveRunPath(stem)
  index = loadIndex(logPath)
  rows: list[dict] = []
  for item in index.get("months") or []:
    events = item.get("events") or []
    if not events:
      continue
    labels = []
    for raw in events:
      eventId, packedNote = _splitEventRef(str(raw))
      labels.append({"id": eventId, "nameJa": _japaneseEventName(eventId, packedNote)})
    rows.append(
      {
        "yearMonth": item.get("yearMonth"),
        "events": events,
        "labels": labels,
        "blurb": item.get("blurb") or "",
      }
    )
  return rows


def listChartMarkers(stem: str) -> list[dict]:
  return chartMarkersFromRows(listEventLog(stem))


def readMonth(stem: str, yearMonth: str) -> dict:
  logPath = resolveRunPath(stem)
  index = loadIndex(logPath)
  offset: int | None = None
  for item in index.get("months") or []:
    if item.get("yearMonth") == yearMonth:
      offset = int(item["offset"])
      break
  if offset is None:
    raise FileNotFoundError(yearMonth)
  with logPath.open("r", encoding="utf-8") as handle:
    handle.seek(offset)
    line = handle.readline()
  return json.loads(line)


def monthView(row: dict) -> dict:
  crowd = row.get("crowd") or {}
  behavior = row.get("behavior") or {}
  law = row.get("law") or {}
  llm = row.get("llm") or {}
  opinion = row.get("opinionLeaders") or {}
  prices = row.get("prices") or {}
  macro = row.get("macro") or {}
  ppp = row.get("purchasingPower") or {}
  fidelity = row.get("historicalFidelity") or {}
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
    "yearMonth": row.get("yearMonth"),
    "standard": row.get("monetaryStandard"),
    "events": _visibleEvents(row),
    "decree": law.get("decree") or "",
    "rulerReason": behavior.get("rulerReason") or llm.get("rulerReason") or "",
    "mascotId": crowd.get("mascotId") or "",
    "mascotSpeech": behavior.get("mascotSpeech") or crowd.get("mascotSpeech") or "",
    "moodText": crowd.get("moodText") or behavior.get("crowdMoodDetail") or "",
    "rumor": crowd.get("rumor") or "",
    "opinionAgents": agents,
    "prices": {
      "zundaPrice": prices.get("zundaPrice"),
      "ankoPrice": prices.get("ankoPrice"),
      "azukiPrice": prices.get("azukiPrice"),
      "ricePrice": prices.get("ricePrice"),
    },
    "population": macro.get("population"),
    "foodBuffer": macro.get("foodBuffer"),
    "purchasingPower": {
      "foodYenPerCapita": ppp.get("foodYenPerCapita") or ppp.get("foodYenPerCapita"),
      "livingVsModern": ppp.get("livingVsModern"),
      "developmentIndex": ppp.get("developmentIndex"),
      "vibe": ppp.get("vibe"),
      "method": ppp.get("method"),
    },
    "fidelity": fidelity.get("score"),
  }


def yearlySeries(stem: str) -> dict:
  logPath = resolveRunPath(stem)
  cachePath = ROOT / "logs" / f"canvas_embed_{stem}.json"
  if cachePath.is_file() and cachePath.stat().st_mtime >= logPath.stat().st_mtime:
    return json.loads(cachePath.read_text(encoding="utf-8"))
  embedSpec = importlib.util.spec_from_file_location(
    "export_canvas_embed",
    ROOT / "scripts" / "export_canvas_embed.py",
  )
  embedMod = importlib.util.module_from_spec(embedSpec)
  assert embedSpec.loader is not None
  embedSpec.loader.exec_module(embedMod)
  rows = embedMod.loadRows(logPath)
  payload = embedMod.yearlyBuckets(rows)
  payload["source"] = str(logPath).replace("\\", "/")
  return payload


def lastYearMonth(stem: str) -> str:
  logPath = resolveRunPath(stem)
  last = ""
  with logPath.open("r", encoding="utf-8") as handle:
    for line in handle:
      if not line.strip():
        continue
      row = json.loads(line)
      last = str(row.get("yearMonth") or last)
  return last


def yearTrace(stem: str, year: int) -> dict:
  prefix = f"{int(year):04d}-"
  months: list[dict] = []
  logPath = resolveRunPath(stem)
  with logPath.open("r", encoding="utf-8") as handle:
    for line in handle:
      if not line.strip():
        continue
      row = json.loads(line)
      yearMonth = str(row.get("yearMonth") or "")
      if not yearMonth.startswith(prefix):
        continue
      view = monthView(row)
      months.append(
        {
          "yearMonth": view["yearMonth"],
          "events": view["events"],
          "decree": view["decree"],
          "mascotSpeech": view["mascotSpeech"],
          "moodText": view["moodText"],
          "rumor": view["rumor"],
          "opinionAgents": view["opinionAgents"],
        }
      )
  return {"stem": stem, "year": int(year), "months": months}


def lifeRecapPaths(stem: str) -> tuple[Path, Path]:
  from src.life_recap import recapPathsForLog

  return recapPathsForLog(resolveRunPath(stem))


def readLifeRecap(stem: str) -> dict:
  jsonPath, _mdPath = lifeRecapPaths(stem)
  if not jsonPath.is_file():
    raise FileNotFoundError("life recap not found")
  return json.loads(jsonPath.read_text(encoding="utf-8"))


def generateLifeRecap(stem: str, useLlm: bool = True) -> dict:
  from src.life_recap import writeLifeRecap

  return writeLifeRecap(resolveRunPath(stem), useLlm=useLlm)


def exportRunZip(stem: str) -> bytes:
  stem = _safeStem(stem)
  logPath = resolveRunPath(stem)
  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(logPath, "monthly.jsonl")
    extras = [logPath.with_name("launch.json"), logPath.with_name("life_recap.json"), logPath.with_name("life_recap.md")]
    if logPath.name == "monthly.jsonl":
      extras = [
        logPath.parent / "launch.json",
        logPath.parent / "life_recap.json",
        logPath.parent / "life_recap.md",
      ]
    for extra in extras:
      if extra.is_file() and extra.name in ALLOWED_ZIP_MEMBERS:
        archive.write(extra, extra.name)
  return buffer.getvalue()


def _stemFromFilename(filename: str) -> str:
  stem = Path(filename or "imported").stem
  stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "imported"
  return _safeStem(stem[:80])


def _uniqueRunStem(base: str) -> str:
  candidate = _safeStem(base)
  stamp = datetime.now().strftime("%Y%m%d%H%M%S")
  suffix = 0
  while True:
    folder = RUNS_DIR / candidate
    flat = RUNS_DIR / f"{candidate}.jsonl"
    if not folder.exists() and not flat.exists():
      return candidate
    suffix += 1
    extra = "" if suffix == 1 else f"_{suffix}"
    candidate = _safeStem(f"{base}_imported_{stamp}{extra}"[:80])


def importRunArchive(raw: bytes, filename: str) -> dict:
  if not raw:
    raise ValueError("empty import")
  if len(raw) > MAX_IMPORT_BYTES:
    raise ValueError("import too large")
  name = Path(filename or "import.zip").name
  lower = name.lower()
  if lower.endswith(".jsonl"):
    stem = _uniqueRunStem(_stemFromFilename(name))
    destDir = RUNS_DIR / stem
    destDir.mkdir(parents=True, exist_ok=True)
    (destDir / "monthly.jsonl").write_bytes(raw)
    return {"stem": stem, "imported": ["monthly.jsonl"]}
  if not zipfile.is_zipfile(io.BytesIO(raw)):
    raise ValueError("import must be zip or jsonl")
  with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
    names: list[str] = []
    for info in archive.infolist():
      if info.is_dir():
        continue
      member = Path(info.filename.replace("\\", "/")).name
      if member.startswith(".") or member not in ALLOWED_ZIP_MEMBERS:
        continue
      names.append(member)
    if "monthly.jsonl" not in names:
      raise ValueError("zip needs monthly.jsonl")
    stem = _uniqueRunStem(_stemFromFilename(name.replace(".zip", "")))
    destDir = RUNS_DIR / stem
    destDir.mkdir(parents=True, exist_ok=True)
    imported: list[str] = []
    for info in archive.infolist():
      if info.is_dir():
        continue
      member = Path(info.filename.replace("\\", "/")).name
      if member not in names:
        continue
      dest = destDir / member
      dest.write_bytes(archive.read(info.filename))
      imported.append(member)
  return {"stem": stem, "imported": imported}


def _canonicalZipMember(filename: str) -> str | None:
  member = Path(str(filename).replace("\\", "/")).name
  if member.startswith("."):
    return None
  if member in ZIP_MEMBER_ALIASES:
    return ZIP_MEMBER_ALIASES[member]
  if member in ALLOWED_ZIP_MEMBERS:
    return member
  return None


def _uniqueCompareStem(base: str) -> str:
  stamp = datetime.now().strftime("%Y%m%d%H%M%S")
  root = _safeStem(f"cmp_{base}"[:40])
  suffix = 0
  while True:
    extra = "" if suffix == 0 else f"_{suffix}"
    candidate = _safeStem(f"{root}_{stamp}{extra}"[:80])
    if not (COMPARE_DIR / candidate).exists():
      return candidate
    suffix += 1


def loadComparePack(raw: bytes, filename: str) -> dict:
  if not raw:
    raise ValueError("empty zip")
  if len(raw) > MAX_IMPORT_BYTES:
    raise ValueError("zip too large")
  name = Path(filename or "run.zip").name
  if not zipfile.is_zipfile(io.BytesIO(raw)):
    raise ValueError("file must be a run zip")
  COMPARE_DIR.mkdir(parents=True, exist_ok=True)
  with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
    mapped: dict[str, str] = {}
    for info in archive.infolist():
      if info.is_dir():
        continue
      canonical = _canonicalZipMember(info.filename)
      if not canonical:
        continue
      mapped[canonical] = info.filename
    if "monthly.jsonl" not in mapped:
      raise ValueError("zip needs monthly.jsonl")
    stem = _uniqueCompareStem(_stemFromFilename(name.replace(".zip", "")))
    destDir = COMPARE_DIR / stem
    destDir.mkdir(parents=True, exist_ok=True)
    imported: list[str] = []
    for canonical, zipName in mapped.items():
      dest = destDir / canonical
      dest.write_bytes(archive.read(zipName))
      imported.append(canonical)
  launch: dict = {}
  launchPath = COMPARE_DIR / stem / "launch.json"
  if launchPath.is_file():
    try:
      parsed = json.loads(launchPath.read_text(encoding="utf-8"))
      if isinstance(parsed, dict):
        launch = parsed
    except (json.JSONDecodeError, OSError):
      launch = {}
  recapPath = COMPARE_DIR / stem / "life_recap.json"
  return {
    "stem": stem,
    "label": Path(name).stem,
    "imported": imported,
    "standard": launch.get("standard"),
    "span": (
      f"{launch.get('start')}..{launch.get('end')}"
      if launch.get("start") and launch.get("end")
      else ""
    ),
    "hasRecap": recapPath.is_file(),
  }
