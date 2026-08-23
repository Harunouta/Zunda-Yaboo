"""Summarize data/events coverage (japan vs world) by decade."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.events import EVENT_TABLE, MONTHLY_EVENTS, getEventPayload, reloadEventData  # noqa: E402


def decadeKey(yearMonth: str) -> str:
  year = int(yearMonth.split("-", 1)[0])
  return f"{year // 10 * 10}s"


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--scope", choices=("all", "japan", "world", "japan_info"), default="all")
  args = parser.parse_args()

  reloadEventData()
  byScope = Counter(payload.scope for payload in EVENT_TABLE.values())
  firings: Counter[str] = Counter()
  for yearMonth, eventIds in MONTHLY_EVENTS.items():
    for eventId in eventIds:
      payload = getEventPayload(eventId)
      if payload is None:
        continue
      if args.scope != "all" and payload.scope != args.scope:
        continue
      firings[decadeKey(yearMonth)] += 1

  print(f"catalog_by_scope={dict(byScope)}")
  print(f"months_with_any_event={len(MONTHLY_EVENTS)}")
  print(f"firings_filter={args.scope}")
  for decade, count in sorted(firings.items()):
    print(f"  {decade}: {count}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
