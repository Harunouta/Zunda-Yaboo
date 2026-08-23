"""Crowd mood helpers (LLM or dry-run) + optional single mascot among commoners."""

from typing import Any

from src.mascot import dryRunMascotSpeech, emptyMascotFields, mascotForStandard

FOOD_HUNGRY = 0.05
FOOD_TIGHT = 0.12
LEGIT_LOW = 0.4
LEGIT_HIGH = 0.75

DRY_RUN_RUMORS = (
  "蔵の米が薄い、との噂が立つ",
  "夜市で砂糖が消えた、と囁かれる",
  "役人の顔が硬い、と茶屋で話す",
  "異国の船の噂が先走りする",
  "藩札の噂で銭箱を抱く者が増える",
  "来月の年貢が跳ねる、と早耳が騒ぐ",
  "豆の出来が良い、と陽気な嘘が飛ぶ",
  "黒船の影を見た、と酔った行商が言う",
)

DRY_RUN_MOODS = (
  "腹は減るが噂は肥える月だ",
  "静かなのに空気が張りつめている",
  "市は動くが笑いが薄い",
  "法令の影より物価の影が長い",
  "腹一杯なら噂も甘くなる",
  "正統性が揺れると舌が尖る",
)


def _stableIndex(yearMonth: str, salt: str, size: int) -> int:
  if size <= 0:
    return 0
  total = sum(ord(ch) for ch in f"{yearMonth}:{salt}")
  return total % size


def dryRunCrowd(
  foodPerCapita: float,
  legitimacy: float,
  hasEvents: bool,
  standard: str = "zunda",
  yearMonth: str = "1603-01",
  decree: str = "",
  events: list[str] | None = None,
) -> dict[str, Any]:
  anger = 0.15
  if foodPerCapita < FOOD_HUNGRY:
    anger += 0.35
  elif foodPerCapita < FOOD_TIGHT:
    anger += 0.15
  if legitimacy < LEGIT_LOW:
    anger += 0.25
  elif legitimacy < LEGIT_HIGH:
    anger += 0.08
  if hasEvents:
    anger += 0.2
  anger = max(min(anger, 1.0), 0.0)

  eventList = events or []
  rumorIndex = _stableIndex(yearMonth, "rumor", len(DRY_RUN_RUMORS))
  moodIndex = _stableIndex(yearMonth, "mood", len(DRY_RUN_MOODS))
  rumor = DRY_RUN_RUMORS[rumorIndex]
  if eventList:
    rumor = f"{rumor}／事件の影: {', '.join(eventList[:2])}"
  moodText = DRY_RUN_MOODS[moodIndex]
  if foodPerCapita < FOOD_HUNGRY:
    moodText = "空腹が噂を辛くする月だ"
  elif legitimacy < LEGIT_LOW:
    moodText = "政権の影が長く、舌が尖る月だ"

  crowdMoodDetail = (
    f"food={foodPerCapita:.3f} legit={legitimacy:.2f} anger={anger:.2f}; "
    f"decree影={decree[:24] if decree else 'なし'}"
  )
  eventReaction = (
    f"事件あり→{', '.join(eventList)}" if eventList else "平穏月→噂だけで腹を満たす"
  )

  mascotId = mascotForStandard(standard)
  result: dict[str, Any] = {
    "rumor": rumor,
    "anger": anger,
    "hoarding": min(anger * 0.8, 1.0),
    "riotRisk": min(anger * 0.6, 1.0),
    "moodText": moodText,
    "crowdMoodDetail": crowdMoodDetail,
    "eventReaction": eventReaction,
    "source": "dry_run",
  }
  if mascotId is None:
    result.update(emptyMascotFields())
  else:
    result["mascotId"] = mascotId
    result["mascotSpeech"] = dryRunMascotSpeech(
      mascotId,
      yearMonth,
      foodPerCapita,
      hasEvents,
      legitimacy=legitimacy,
      events=eventList,
      decree=decree,
    )
  return result


def summarizePolicy(policy: dict[str, Any] | None) -> str:
  if not policy:
    return "政策メモなし"
  processRatio = float(policy.get("processBeansRatio", 0.0))
  reserve = float(policy.get("reserveReleaseRatio", 0.0))
  trade = str(policy.get("tradeStance", "closed"))
  crackdown = float(policy.get("blackMarketCrackdown", 0.0))
  bits = [
    f"豆加工{processRatio:.0%}",
    f"備蓄放出{reserve:.0%}",
    f"交易={trade}",
  ]
  if crackdown > 0.05:
    bits.append(f"闇市取締{crackdown:.0%}")
  return "／".join(bits)


def synthesizeRulerReason(
  decree: str,
  events: list[str],
  decisionSource: str,
  yearMonth: str,
) -> str:
  if decisionSource.startswith("llm") and not decisionSource.startswith("llm_fallback"):
    if decree:
      return f"LLM裁定: {decree[:60]}"
    return f"{yearMonth} のLLM裁定（布告本文は空）"
  if events:
    return f"事件対応({', '.join(events[:2])}): {decree[:48] or '定例統治'}"
  templates = (
    f"定例統治: {decree[:48] or '年貢と通貨の手入れ'}",
    f"静かな月の舵取り: {decree[:48] or '相場監視のみ'}",
    f"帳簿の月: {decree[:48] or '備蓄と税の微調整'}",
  )
  return templates[_stableIndex(yearMonth, "ruler", len(templates))]


def buildBehaviorLog(
  *,
  yearMonth: str,
  decree: str,
  decisionSource: str,
  policy: dict[str, Any] | None,
  crowd: dict[str, Any],
  events: list[str],
  foodPerCapita: float,
  legitimacy: float,
  rulerReason: str = "",
) -> dict[str, Any]:
  reason = rulerReason or synthesizeRulerReason(decree, events, decisionSource, yearMonth)
  moodDetail = str(crowd.get("crowdMoodDetail") or crowd.get("moodText") or "")
  if not moodDetail:
    moodDetail = f"food={foodPerCapita:.3f} legit={legitimacy:.2f}"
  eventReaction = str(crowd.get("eventReaction") or "")
  if not eventReaction:
    eventReaction = (
      f"事件あり→{', '.join(events)}" if events else "平穏月→日常の噂"
    )
  return {
    "rulerReason": reason,
    "policySummary": summarizePolicy(policy),
    "crowdMoodDetail": moodDetail,
    "eventReaction": eventReaction,
    "mascotSpeech": str(crowd.get("mascotSpeech") or ""),
  }
