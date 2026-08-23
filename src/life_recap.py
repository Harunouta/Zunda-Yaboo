"""Post-run life recap. Does not change sim coefficients."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.mascot import mascotForStandard

NOISE_EVENT_IDS = frozenset({"riot_risk", "riot_risk"})
MAX_SNAPSHOTS = 90
MAX_EVENTS = 40
MAX_SPEECHES = 24


def recapPathsForLog(logPath: Path) -> tuple[Path, Path]:
  if logPath.name == "monthly.jsonl":
    folder = logPath.parent
    return folder / "life_recap.json", folder / "life_recap.md"
  return logPath.with_name(logPath.stem + "_life_recap.json"), logPath.with_name(
    logPath.stem + "_life_recap.md"
  )


def _visibleEvents(row: dict) -> list[str]:
  return [str(item) for item in (row.get("events") or []) if item not in NOISE_EVENT_IDS]


def _speech(row: dict) -> str:
  crowd = row.get("crowd") or {}
  behavior = row.get("behavior") or {}
  return str(behavior.get("mascotSpeech") or crowd.get("mascotSpeech") or "").strip()


def _mascotId(row: dict) -> str | None:
  crowd = row.get("crowd") or {}
  mascotId = crowd.get("mascotId") or None
  if mascotId:
    return str(mascotId)
  return mascotForStandard(str(row.get("monetaryStandard") or ""))


def digestLog(logPath: Path) -> dict[str, Any]:
  rows: list[dict] = []
  with logPath.open("r", encoding="utf-8") as handle:
    for line in handle:
      if not line.strip():
        continue
      rows.append(json.loads(line))
  if not rows:
    raise ValueError("empty log")
  first = rows[0]
  last = rows[-1]
  eventCounts: Counter[str] = Counter()
  speeches: list[str] = []
  mascotVotes: Counter[str] = Counter()
  snapshots: list[dict] = []
  step = max(1, len(rows) // MAX_SNAPSHOTS)
  for index, row in enumerate(rows):
    events = _visibleEvents(row)
    eventCounts.update(events)
    mascotId = _mascotId(row)
    if mascotId:
      mascotVotes[mascotId] += 1
    speech = _speech(row)
    keep = (
      index == 0
      or index == len(rows) - 1
      or index % step == 0
      or bool(events)
      or bool(speech)
    )
    if keep and (len(snapshots) < MAX_SNAPSHOTS or events or speech):
      if len(snapshots) >= MAX_SNAPSHOTS and not events:
        continue
      ppp = row.get("purchasingPower") or {}
      macro = row.get("macro") or {}
      fidelity = row.get("historicalFidelity") or {}
      snapshots.append(
        {
          "yearMonth": row.get("yearMonth"),
          "standard": row.get("monetaryStandard"),
          "population": macro.get("population"),
          "foodYen": ppp.get("foodYenPerCapita") or ppp.get("foodYenPerCapita"),
          "vibe": ppp.get("vibe"),
          "fidelity": fidelity.get("score"),
          "events": events[:6],
          "speech": speech[:120] if speech else "",
        }
      )
      if speech and len(speeches) < MAX_SPEECHES:
        speeches.append(f"{row.get('yearMonth')}: {speech[:160]}")
  voice = mascotVotes.most_common(1)[0][0] if mascotVotes else None
  topEvents = [{"id": eventId, "months": count} for eventId, count in eventCounts.most_common(MAX_EVENTS)]
  return {
    "start": first.get("yearMonth"),
    "end": last.get("yearMonth"),
    "monthCount": len(rows),
    "voice": voice,
    "startPop": (first.get("macro") or {}).get("population"),
    "endPop": (last.get("macro") or {}).get("population"),
    "startFoodYen": (first.get("purchasingPower") or {}).get("foodYenPerCapita")
    or (first.get("purchasingPower") or {}).get("foodYenPerCapita"),
    "endFoodYen": (last.get("purchasingPower") or {}).get("foodYenPerCapita")
    or (last.get("purchasingPower") or {}).get("foodYenPerCapita"),
    "topEvents": topEvents,
    "speeches": speeches,
    "snapshots": snapshots[-MAX_SNAPSHOTS:],
  }


def _dryRecap(digest: dict[str, Any]) -> dict[str, Any]:
  voice = digest.get("voice")
  start = digest.get("start")
  end = digest.get("end")
  lines = [
    f"{start}から{end}まで、{digest.get('monthCount')}ヶ月を暮らした記録。",
    f"人口は {digest.get('startPop')} から {digest.get('endPop')} へ。",
    f"食/人円は {digest.get('startFoodYen')} から {digest.get('endFoodYen')} へ。",
  ]
  if digest.get("topEvents"):
    names = ", ".join(item["id"] for item in digest["topEvents"][:12])
    lines.append(f"よく来た出来事: {names}。")
  if voice == "zundamon":
    title = "ずんだもんの総括なのだ"
    body = (
      "\n\n".join(lines)
      + "\n\n長いあいだ市を歩いたのだ。腹と噂と法令が代わる代わる押してきたのだ。"
      " ずんだが近い月は頬がゆるむのだ。遠い月は餅の予定を先に延ばすのだ。"
      " 数字は上の通り。細かい凸凹は月次のセリフに残しているのだ。"
    )
  elif voice == "ankomon":
    title = "あんこもんの総括もん"
    body = (
      "\n\n".join(lines)
      + "\n\nあんこ以外は認めないもん。長い期間でも甘い備蓄で測るもん。"
      " 騒動の月は蔵を疑うもん。平和な月は餡の順番を守るもん。"
    )
  else:
    title = "市井の暮らしの変遷"
    body = (
      "\n\n".join(lines)
      + "\n\nマスコットはいなかった。普通の町の者として、米と銭と噂の距離が年月で伸び縮みした。"
      " 飢饉や争いの年は蔵と人の顔色が先に変わる。平和な年は値段の話が日常に戻る。"
      " 以下は拾った月の断片である。\n\n"
      + "\n".join(digest.get("speeches") or [])
    )
  return {"title": title, "recap": body, "voice": voice or "commoner", "source": "dry"}


def _llmRecap(digest: dict[str, Any]) -> dict[str, Any]:
  from src.llm_client import callLifeRecap

  voice = digest.get("voice")
  userPrompt = (
    "この期間をあなた自身が暮らしたとして、総括を長く書いてください。"
    " 月次の一言ではなく、食・値段・恐れ・法令・祭りの移り変わりを段落で。"
    " 事実は次のダイジェストに合わせ、ない出来事は作らない。\n\n"
    + json.dumps(
      {
        "start": digest.get("start"),
        "end": digest.get("end"),
        "monthCount": digest.get("monthCount"),
        "startPop": digest.get("startPop"),
        "endPop": digest.get("endPop"),
        "startFoodYen": digest.get("startFoodYen"),
        "endFoodYen": digest.get("endFoodYen"),
        "topEvents": digest.get("topEvents"),
        "speeches": digest.get("speeches"),
        "snapshots": digest.get("snapshots")[:40],
      },
      ensure_ascii=False,
    )
  )
  raw = callLifeRecap(userPrompt, voice if voice in ("zundamon", "ankomon") else None)
  return {
    "title": raw.get("title") or "暮らしの総括",
    "recap": raw.get("recap") or "",
    "voice": voice or "commoner",
    "source": "llm",
    "modelUsed": raw.get("modelUsed"),
  }


def writeLifeRecap(logPath: Path, useLlm: bool = True) -> dict[str, Any]:
  digest = digestLog(logPath)
  try:
    payload = _llmRecap(digest) if useLlm else _dryRecap(digest)
  except Exception as error:
    payload = _dryRecap(digest)
    payload["llmError"] = str(error)
  payload["digest"] = {
    "start": digest.get("start"),
    "end": digest.get("end"),
    "monthCount": digest.get("monthCount"),
    "voice": digest.get("voice"),
    "topEvents": digest.get("topEvents")[:15],
  }
  jsonPath, mdPath = recapPathsForLog(logPath)
  jsonPath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
  mdPath.write_text(
    f"# {payload.get('title')}\n\n{payload.get('recap')}\n",
    encoding="utf-8",
  )
  return payload
