"""Build a post-run life recap from monthly JSONL. Does not change the engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.life_recap import writeLifeRecap


def main() -> int:
  parser = argparse.ArgumentParser(description="Write mascot/commoner life recap for a run log")
  parser.add_argument("--log", required=True, help="Path to monthly JSONL")
  parser.add_argument("--no-llm", action="store_true", help="Numbers-only dry recap")
  args = parser.parse_args()
  payload = writeLifeRecap(Path(args.log), useLlm=not args.no_llm)
  print(payload.get("title"))
  print(payload.get("source"))
  print((payload.get("recap") or "")[:500])
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
