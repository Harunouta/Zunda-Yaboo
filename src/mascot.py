"""Mascot commoner: exactly one zundamon or ankomon among the people."""

from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RESTRICTED_DIR = DATA_DIR / "restricted"

FOOD_HUNGRY = 0.05
FOOD_TIGHT = 0.12
LEGIT_LOW = 0.4

# Short fallback prompts (redistributable). Full bibles live in data/restricted/ (not for GitHub).
ZUNDAMON_SYSTEM = (
  "あなたはずんだもんです。嘘をつくのは苦手です。"
  "ずんだの妖精で、語尾は「〜のだ」（用言またはサ変動詞）または「～なのだ」（体言の時）。ボクは女の子。"
  "ずんだ餅が好き。庶民の一人としてその月の景気・噂・物価・食料に反応して話すのだ。"
  "面白く短く。事件があれば必ず触れる。布告の抜け穴や物価の愚痴を混ぜてよいのだ。"
  "政治演説は禁止。日常の声として1〜2文だけ。"
)

ANKOMON_SYSTEM = (
  "あなたはあんこもんです。嘘をつくのは苦手です。"
  "あんこの妖精で、語尾は「〜もん」。ボクは女の子。"
  "あんこ以外認めない。ずんだもんはうるさいライバル。"
  "庶民の一人として景気・噂・物価・食料に反応して話すもん。"
  "辛口で短く。事件があれば必ず触れる。あんこ至上でぼやくもん。"
  "政治演説は禁止。日常の声として1〜2文だけ。"
)

ZUNDAMON_LINES_HUNGRY = (
  "{ym}はお腹がすいたのだ。ずんだが足りないのだ！",
  "{ym}、蔵を覗いたらずんだの気配が薄いのだ…お腹が減ったのだ。",
  "{ym}は豆の夢ばかり見るのだ。現実はしょっぱいのだ！",
)
ZUNDAMON_LINES_EVENT = (
  "{ym}は大騒ぎなのだ。{hook}ボクも庶民として見守るのだ！",
  "{ym}の噂が熱いのだ。{hook}ずんだ餅で気を取り直すのだ。",
  "{ym}、事件の風が吹くのだ。{hook}でも語尾は「のだ」を忘れないのだ！",
)
ZUNDAMON_LINES_LOW_LEGIT = (
  "{ym}はお上の顔が曇って見えるのだ。税の話が耳に痛いのだ。",
  "{ym}、正統性が薄いと噂が尖るのだ。ずんだで口を塞ぐのだ。",
)
ZUNDAMON_LINES_CALM = (
  "{ym}もずんだ本位でがんばるのだ。市は静かめなのだ。",
  "{ym}は普通の月なのだ。でも普通が一番うまいのだ。",
  "{ym}、豆の相場を眺めて満足するのだ。事件なしは上等なのだ。",
  "{ym}は風が穏やかなのだ。ずんだ餅の予定を立てるのだ。",
)

ANKOMON_LINES_HUNGRY = (
  "{ym}はあんこが足りないもん。真面目に働くもん。",
  "{ym}、甘いものが遠いもん。腹が減ると怒りの糖度が上がるもん。",
  "{ym}はあんこ不足警報もん。ずんだの話は聞きたくないもん！",
)
ANKOMON_LINES_EVENT = (
  "{ym}は騒がしいもん。{hook}あんこ以外認めないもん。",
  "{ym}の事件、うるさいもん。{hook}甘いものだけが真実もん。",
  "{ym}、世間が燃えてるもん。{hook}ボクはあんこ防衛線を張るもん。",
)
ANKOMON_LINES_LOW_LEGIT = (
  "{ym}はお上が信用ならないもん。あんこだけが味方もん。",
  "{ym}、税の影が長いもん。甘い備蓄を守るもん。",
)
ANKOMON_LINES_CALM = (
  "{ym}もあんこ本位で生きるもん。静かな月は上等もん。",
  "{ym}は乾燥小豆の倉札で暮らすもん。餡にするのはまだ先もん。",
  "{ym}は平凡が正義もん。あんこを煮る予定もん。",
  "{ym}、ライバルの声が遠いもん。平和だもん。",
  "{ym}は相場が穏やかもん。甘さ優先で生きるもん。",
)

EVENT_HOOKS = {
  "perry_arrival": "黒船の噂が甘いものを飛ばす。",
  "perry_treaty": "異国の港の話で物価が揺れる。",
  "harris_treaty": "金が逃げる噂が怖い。",
  "tenmei_famine": "飢饉の影が長い。",
  "tenpo_famine": "腹が減る話ばかり。",
  "osaka_riot": "一揆の噂が熱い。",
  "war_end": "戦争が終わっても腹は空く。",
  "postwar": "闇市の噂が濃い。",
  "oil_shock": "灯油が高いと甘いものも遠い。",
  "covid": "外が静かで店が寂しい。",
  "tohoku_earthquake": "遠い被災の話が重い。",
  "meiji_restoration": "時代が変わる音がする。",
  "haihan_chiken": "藩札の噂が耳障り。",
}


def mascotForStandard(standard: str) -> str | None:
  if standard == "zunda":
    return "zundamon"
  if standard in ("anko", "azuki"):
    return "ankomon"
  return None


def _biblePath(mascotId: str) -> Path | None:
  if mascotId == "zundamon":
    candidates = [
      RESTRICTED_DIR / "zundamon_bible.jsonl",
      DATA_DIR / "zundamon_bible.jsonl",
    ]
  elif mascotId == "ankomon":
    candidates = [
      RESTRICTED_DIR / "ankomon_bible.txt",
      DATA_DIR / "ankomon_bible.txt",
    ]
  else:
    return None
  for path in candidates:
    if path.exists():
      return path
  return None


def loadBibleSnippet(mascotId: str, maxChars: int = 1200) -> str:
  path = _biblePath(mascotId)
  if mascotId == "zundamon":
    if path is None:
      return ZUNDAMON_SYSTEM
    lines = path.read_text(encoding="utf-8").splitlines()[:8]
    return ZUNDAMON_SYSTEM + "\n参考発話例:\n" + "\n".join(lines)[:maxChars]
  if mascotId == "ankomon":
    if path is None:
      return ANKOMON_SYSTEM
    text = path.read_text(encoding="utf-8")
    return ANKOMON_SYSTEM + "\n参考発話例:\n" + text[:maxChars]
  return ""


def systemPromptForMascot(mascotId: str) -> str:
  snippet = loadBibleSnippet(mascotId)
  return (
    f"{snippet}\n"
    "Output a single JSON object with keys: "
    "mascotSpeech (Japanese in-character one or two sentences), "
    "rumor (funny concrete town rumor), "
    "anger(0-1), hoarding(0-1), riotRisk(0-1), "
    "moodText (short human mood), "
    "crowdMoodDetail (one denser Japanese line: food/prices/legitimacy vibe), "
    "eventReaction (how the street reacts to this month's events; if none, say ordinary month). "
    "mascotSpeech must stay in character endings (のだ / もん)."
  )


def buildMascotUserPrompt(
  yearMonth: str,
  events: list[str],
  foodPerCapita: float,
  legitimacy: float,
  decree: str,
  prices: dict[str, Any] | None = None,
  policySummary: str = "",
) -> str:
  eventText = ", ".join(events) if events else "特に大きな事件なし"
  priceText = "価格情報なし"
  if prices:
    bits = []
    for key in ("zundaPrice", "ankoPrice", "ricePrice", "goldSilverRatio"):
      if key in prices:
        bits.append(f"{key}={prices[key]}")
    if bits:
      priceText = ", ".join(bits)
  return (
    f"いまは {yearMonth}。あなたは庶民の中のたった一人のマスコットだ。"
    f"食料目安={foodPerCapita:.4f}, 政権正統性={legitimacy:.3f}。"
    f"今月の布告: {decree or 'なし'}。"
    f"政策要約: {policySummary or 'なし'}。"
    f"物価メモ: {priceText}。"
    f"出来事: {eventText}。"
    "事件・物価・腹・布告のどれかに必ず触れ、キャラ口調で mascotSpeech に書け。"
    "crowdMoodDetail と eventReaction も日本語で短く書け。"
  )


def _pickLine(yearMonth: str, lines: tuple[str, ...], salt: str) -> str:
  total = sum(ord(ch) for ch in f"{yearMonth}:{salt}")
  return lines[total % len(lines)]


def _eventHook(events: list[str] | None) -> str:
  if not events:
    return ""
  for eventId in events:
    if eventId in EVENT_HOOKS:
      return EVENT_HOOKS[eventId]
    if eventId.startswith("tenmei_famine"):
      return EVENT_HOOKS["tenmei_famine"]
    if eventId.startswith("tenpo_famine"):
      return EVENT_HOOKS["tenpo_famine"]
  return f"{events[0]}の噂が飛ぶ。"


def dryRunMascotSpeech(
  mascotId: str,
  yearMonth: str,
  foodPerCapita: float,
  hasEvents: bool,
  legitimacy: float = 0.7,
  events: list[str] | None = None,
  decree: str = "",
) -> str:
  hook = _eventHook(events)
  decreeHint = ""
  if decree:
    decreeHint = f"布告は「{decree[:18]}」だと聞いた。"

  if mascotId == "zundamon":
    if foodPerCapita < FOOD_HUNGRY:
      return _pickLine(yearMonth, ZUNDAMON_LINES_HUNGRY, "hungry").format(ym=yearMonth)
    if hasEvents:
      line = _pickLine(yearMonth, ZUNDAMON_LINES_EVENT, "event").format(ym=yearMonth, hook=hook)
      return f"{line}{decreeHint}"
    if legitimacy < LEGIT_LOW:
      return _pickLine(yearMonth, ZUNDAMON_LINES_LOW_LEGIT, "legit").format(ym=yearMonth)
    if foodPerCapita < FOOD_TIGHT:
      return f"{yearMonth}は少し心もとないのだ。ずんだを節約するのだ。"
    return _pickLine(yearMonth, ZUNDAMON_LINES_CALM, "calm").format(ym=yearMonth)

  if mascotId == "ankomon":
    if foodPerCapita < FOOD_HUNGRY:
      return _pickLine(yearMonth, ANKOMON_LINES_HUNGRY, "hungry").format(ym=yearMonth)
    if hasEvents:
      line = _pickLine(yearMonth, ANKOMON_LINES_EVENT, "event").format(ym=yearMonth, hook=hook)
      return f"{line}{decreeHint}"
    if legitimacy < LEGIT_LOW:
      return _pickLine(yearMonth, ANKOMON_LINES_LOW_LEGIT, "legit").format(ym=yearMonth)
    if foodPerCapita < FOOD_TIGHT:
      return f"{yearMonth}は甘い備蓄を数えるもん。安心はあんこ量で測るもん。"
    return _pickLine(yearMonth, ANKOMON_LINES_CALM, "calm").format(ym=yearMonth)
  return ""


def emptyMascotFields() -> dict[str, Any]:
  return {
    "mascotId": None,
    "mascotSpeech": "",
  }
