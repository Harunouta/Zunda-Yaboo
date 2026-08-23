"""Terminal ticker: replay a JSONL run so mascot lines pop month-by-month.

Examples:
  python scripts/play_run.py --log logs/runs/founding_tenmei_1780_1790.jsonl --delay 0.35
  python scripts/play_run.py --log logs/runs/world_covid_to_2026.jsonl --only-events --delay 0.5
  python scripts/play_run.py --live --standard zunda --start 1853-01 --end 1853-12 --delay 0.4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.economy import STANDARD_CHOICES  # noqa: E402

CLEAR = "\033[2J\033[H" if os.getenv("ZUNDA_PLAY_CLEAR", "1") == "1" else ""


def loadRows(path: Path) -> list[dict]:
  rows: list[dict] = []
  for line in path.read_text(encoding="utf-8").splitlines():
    if line.strip():
      rows.append(json.loads(line))
  return rows


def pickSpeech(row: dict) -> str:
  crowd = row.get("crowd") or {}
  behavior = row.get("behavior") or {}
  return str(behavior.get("mascotSpeech") or crowd.get("mascotSpeech") or "").strip()


def formatFrame(row: dict, index: int, total: int) -> str:
  yearMonth = row.get("yearMonth", "?")
  events = row.get("events") or []
  crowd = row.get("crowd") or {}
  law = row.get("law") or {}
  prices = row.get("prices") or {}
  macro = row.get("macro") or {}
  governance = row.get("governance") or {}
  opinion = row.get("opinionLeaders") or {}
  ppp = row.get("purchasingPower") or {}
  speech = pickSpeech(row)
  mascotId = crowd.get("mascotId") or "-"
  regionMode = governance.get("regionMode") or (opinion.get("region") or {}).get("mode") or "-"

  yenLine = ""
  if ppp:
    yenLine = (
      f"  yen≈     : zunda¥{ppp.get('zundaYen')}  anko¥{ppp.get('ankoYen')}  "
      f"azuki¥{ppp.get('azukiYen')}  "
      f"food/人¥{ppp.get('foodYenPerCapita')}  "
      f"vs今{round(float(ppp.get('livingVsModern') or 0)*100, 2)}%  "
      f"×{ppp.get('developmentIndex')}  {ppp.get('vibe')}"
    )
    if ppp.get("dollarYen"):
      yenLine += f"\n  dollar≈  : ¥{ppp.get('dollarYen')}/USD  fx={ppp.get('fxYenPerDollar')}  sim={prices.get('dollarPrice')}"
  else:
    # Retrofit on old logs without purchasingPower block.
    try:
      from src.purchasing_power import computePurchasingPower

      population = float(macro.get("population") or 1.0)
      food = float(macro.get("foodBuffer") or 0.0) / max(population, 1.0)
      live = computePurchasingPower(
        zundaPrice=float(prices.get("zundaPrice") or 1.0),
        ankoPrice=float(prices.get("ankoPrice") or 1.0),
        azukiPrice=float(prices.get("azukiPrice") or 0.0),
        ricePrice=float(prices.get("ricePrice") or 1.0),
        foodPerCapita=food,
        goldSilverRatio=float(macro.get("goldSilverRatio") or prices.get("goldPrice") or 1.0),
        year=int(str(yearMonth)[:4]) if str(yearMonth)[:4].isdigit() else 1603,
      )
      yenLine = (
        f"  yen≈     : zunda¥{live.zundaYen:.1f}  anko¥{live.ankoYen:.1f}  "
        f"azuki¥{live.azukiYen:.1f}  "
        f"food/人¥{live.foodYenPerCapita:.1f}  "
        f"vs今{live.livingVsModern*100:.2f}%  ×{live.developmentIndex:.2f}  {live.vibe}"
      )
    except Exception:
      yenLine = ""

  banner = "=" * 60
  lines = [
    banner,
    f"  Zunda-Yaboo  {yearMonth}   [{index + 1}/{total}]",
    banner,
    f"  events   : {', '.join(str(e) for e in events) if events else '(quiet month)'}",
    f"  decree   : {law.get('decree', '')}",
    f"  pop/food : {macro.get('population')} / {macro.get('foodBuffer')}",
    f"  prices   : zunda={prices.get('zundaPrice')}  anko={prices.get('ankoPrice')}  "
    f"azuki={prices.get('azukiPrice')}  rice={prices.get('ricePrice')}",
  ]
  climate = row.get("climate") or {}
  if climate:
    lines.append(
      f"  climate  : idx={climate.get('index')}  disaster={climate.get('disasterMultiplier')}  "
      f"src={climate.get('source')}"
    )
  notesBits = [
    f"zunda札={macro.get('zundaNotes')}",
    f"anko札={macro.get('ankoNotes')}",
    f"azuki札={macro.get('azukiNotes')}",
    f"小豆倉={macro.get('azukiStock')}",
  ]
  lines.append("  notes    : " + "  ".join(notesBits))
  mediators = row.get("mediators") or {}
  national = mediators.get("national") if isinstance(mediators, dict) else None
  if isinstance(national, dict):
    lines.append(
      f"  mediate  : unrest={national.get('socialUnrest')}  "
      f"trust={national.get('fiatTrust')}  spoil={national.get('stockSpoilage')}"
    )
  if yenLine:
    lines.append(yenLine)
  fidelity = row.get("historicalFidelity") or {}
  if fidelity:
    lines.append(
      f"  fidelity : score={fidelity.get('score')}  riceErr={fidelity.get('riceErr')}  "
      f"legitErr={fidelity.get('legitimacyErr')}"
    )
  lines.extend([
    f"  legit    : {governance.get('legitimacy')}   taxEff={governance.get('effectiveTaxRate')}   region={regionMode}",
    f"  mood     : {crowd.get('moodText') or (row.get('behavior') or {}).get('crowdMoodDetail', '')}",
    f"  rumor    : {crowd.get('rumor', '')}",
    "",
  ])
  if opinion.get("active"):
    lines.append(f"  opinion  : ON  trigger={opinion.get('trigger', [])}")
    for agent in (opinion.get("agents") or [])[:3]:
      lines.append(
        f"    - {agent.get('agentId')} [{agent.get('intent')}] {str(agent.get('rumor', ''))[:48]}"
      )
    lines.append("")

  lines.append(f"  [{mascotId}]")
  if speech:
    lines.append("")
    lines.append(f"     「{speech}」")
  else:
    lines.append("     （セリフなし — dry-run フォールバック月）")
  lines.append("")
  lines.append(banner)
  return "\n".join(lines)


def playRows(rows: list[dict], delaySec: float) -> None:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  total = len(rows)
  for index, row in enumerate(rows):
    frame = formatFrame(row, index, total)
    if CLEAR:
      sys.stdout.write(CLEAR)
    sys.stdout.write(frame + "\n")
    sys.stdout.flush()
    if delaySec > 0 and index < total - 1:
      time.sleep(delaySec)


def runLive(args: argparse.Namespace) -> Path:
  from src.main import main as unusedMain  # noqa: F401 — ensure package importable
  from src.monthly_engine import runMonthlySimulation

  logPath = Path(args.liveLog)
  logPath.parent.mkdir(parents=True, exist_ok=True)
  if logPath.exists():
    logPath.unlink()
  runMonthlySimulation(
    standard=args.standard,
    start=args.start,
    end=args.end,
    useLlm=bool(args.llm),
    resume=False,
    historicalPolicy=False,
    logPath=logPath,
    opinionLeaderCount=int(args.opinionLeaders),
    opinionParallel=False,
  )
  return logPath


PRESETS = {
  "full-zunda": ROOT / "logs" / "runs" / "zunda_full_1603_2026.jsonl",
  "tenmei": ROOT / "logs" / "runs" / "tonight_tenmei_famine_1780_1790.jsonl",
  "covid-modern": ROOT / "logs" / "runs" / "world_covid_to_2026.jsonl",
  "perry": ROOT / "logs" / "runs" / "play_peek_1853.jsonl",
  "world-modern": ROOT / "logs" / "runs" / "world_era_1801_2026.jsonl",
  "floods-1950s": ROOT / "logs" / "runs" / "tonight_floods_1953_1959.jsonl",
  "azuki-tenmei": ROOT / "logs" / "runs" / "tonight_azuki_tenmei.jsonl",
  "azuki-1853": ROOT / "logs" / "runs" / "tonight_azuki_llm_1853.jsonl",
  "historical-full": ROOT / "logs" / "runs" / "historical_1603_2026.jsonl",
}


def main() -> int:
  parser = argparse.ArgumentParser(description="Pop mascot lines month-by-month in the terminal")
  parser.add_argument("--log", type=Path, help="Existing JSONL to replay")
  parser.add_argument(
    "--preset",
    choices=tuple(PRESETS.keys()),
    default="",
    help="Convenience log presets under logs/runs/",
  )
  parser.add_argument("--delay", type=float, default=0.45, help="Seconds between months")
  parser.add_argument("--only-events", action="store_true", help="Skip quiet months")
  parser.add_argument("--tail", type=int, default=0, help="Only last N months (0=all)")
  parser.add_argument("--live", action="store_true", help="Run a short sim then play it")
  parser.add_argument("--live-log", dest="liveLog", default="logs/runs/play_live_demo.jsonl")
  parser.add_argument("--standard", default="zunda", choices=STANDARD_CHOICES)
  parser.add_argument("--start", default="1853-01")
  parser.add_argument("--end", default="1853-12")
  parser.add_argument("--llm", action="store_true", help="Use LM Studio for live run")
  parser.add_argument("--opinion-leaders", dest="opinionLeaders", type=int, default=5)
  args = parser.parse_args()

  if args.live:
    print("Running live short sim…", flush=True)
    logPath = runLive(args)
    print(f"Wrote {logPath}, starting ticker…", flush=True)
    time.sleep(0.4)
  elif args.preset:
    logPath = PRESETS[args.preset]
  elif args.log:
    logPath = args.log
  else:
    parser.error("Provide --log PATH, --preset NAME, or --live")

  rows = loadRows(logPath)
  if args.only_events:
    rows = [row for row in rows if row.get("events")]
  if args.tail > 0:
    rows = rows[-args.tail :]
  if not rows:
    print("No months to play.")
    return 1

  print(f"Playing {len(rows)} months from {logPath} (delay={args.delay}s). Ctrl+C to stop.", flush=True)
  time.sleep(0.6)
  try:
    playRows(rows, args.delay)
  except KeyboardInterrupt:
    print("\nStopped.")
    return 130
  print("\nDone.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
