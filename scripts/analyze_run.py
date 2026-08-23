"""Simple log analysis helper: event counts, speech samples, region flips, anomalies."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def loadRows(path: Path) -> list[dict]:
  return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
  parser = argparse.ArgumentParser(description="Summarize a monthly JSONL run")
  parser.add_argument("--log", required=True, type=Path)
  parser.add_argument("--speech", type=int, default=8, help="How many mascot lines to sample")
  args = parser.parse_args()

  rows = loadRows(args.log)
  print(f"log={args.log} months={len(rows)}")
  if not rows:
    return 1

  print(f"range={rows[0].get('yearMonth')} .. {rows[-1].get('yearMonth')}")
  print(
    f"pop {rows[0].get('macro', {}).get('population')} -> {rows[-1].get('macro', {}).get('population')}"
  )

  eventCounter: Counter[str] = Counter()
  speechSamples: list[str] = []
  flips: list[str] = []
  regionModes: Counter[str] = Counter()
  for row in rows:
    for eventId in row.get("events") or []:
      if eventId != "riot_risk":
        eventCounter[str(eventId)] += 1
    crowd = row.get("crowd") or {}
    behavior = row.get("behavior") or {}
    speech = behavior.get("mascotSpeech") or crowd.get("mascotSpeech")
    if speech and len(speechSamples) < args.speech:
      speechSamples.append(f"{row.get('yearMonth')}: {speech}")
    opinion = row.get("opinionLeaders") or {}
    region = opinion.get("region") or {}
    if region.get("flippedThisMonth"):
      flips.append(f"{row.get('yearMonth')} peak={region.get('peakFoundingInfluence')}")
    mode = (row.get("governance") or {}).get("regionMode") or region.get("mode")
    if mode:
      regionModes[str(mode)] += 1

  print("\n# top events")
  for eventId, count in eventCounter.most_common(15):
    print(f"  {eventId}: {count}")

  print("\n# region modes", dict(regionModes))
  if flips:
    print("# founding flips")
    for item in flips:
      print(f"  {item}")

  try:
    from src.purchasing_power import summarizeEra

    yearly = summarizeEra(rows)
    if yearly:
      first = yearly[0]
      last = yearly[-1]
      print("\n# purchasing power (rice PPP → modern yen)")
      print(
        f"  {first['year']}: food¥{first['foodYenPerCapita']} "
        f"vs今{first['livingVsModernPct']}% {first['vibe']}"
      )
      print(
        f"  {last['year']}: food¥{last['foodYenPerCapita']} "
        f"vs今{last['livingVsModernPct']}% ×{last['developmentIndex']} {last['vibe']}"
      )
      print(
        f"  tip: python scripts/export_purchasing_power.py --log {args.log}"
      )
  except Exception as exc:
    print(f"\n# purchasing power skipped ({exc})")

  print("\n# mascot samples")
  for sample in speechSamples:
    print(f"  {sample}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
