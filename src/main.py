"""CLI entry: monetary standard radio + monthly run to 2026-08."""

import argparse
import json
import os
import sys
from pathlib import Path

from src.economy import STANDARD_CHOICES
from src.monthly_engine import runMonthlySimulation
from src.opinion_agents import DEFAULT_OPINION_LEADER_COUNT


WORKSPACE = Path(__file__).resolve().parents[1]


def _envBool(name: str, default: bool = False) -> bool:
  raw = os.getenv(name)
  if raw is None:
    return default
  return raw.strip().lower() in ("1", "true", "yes", "on")


def buildParser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description=(
      "Zunda-Yaboo monthly Edo-bakufu simulation. "
      "Standards: zunda | anko | azuki | edo_metal | gold_yen | dollar | historical. "
      "historical = Edo metal → gold yen (1897) → dollar (1949)."
    )
  )
  parser.add_argument(
    "--standard",
    choices=list(STANDARD_CHOICES) + ["historical"],
    default="zunda",
    help="Monetary regime. historical follows data/economy/monetary_regimes.csv",
  )
  parser.add_argument("--start", default="1603-01", help="Start year-month YYYY-MM")
  parser.add_argument("--end", default="2026-08", help="End year-month YYYY-MM")
  parser.add_argument("--llm", dest="useLlm", action="store_true", default=True, help="Enable monthly LLM (default)")
  parser.add_argument("--no-llm", dest="useLlm", action="store_false", help="Dry-run without LM Studio")
  parser.add_argument("--resume", action="store_true", help="Resume from checkpoints/latest.json")
  parser.add_argument(
    "--historical-policy",
    action="store_true",
    help="History-following policy knobs (metal/gold/dollar). Validity baseline uses this with edo_metal.",
  )
  parser.add_argument("--probe", action="store_true", help="Probe LM Studio models and exit")
  parser.add_argument("--validate-baseline", action="store_true", help="Run validity baselines and exit")
  parser.add_argument(
    "--log",
    default=None,
    help="Monthly JSONL output path (default: logs/monthly_run.jsonl)",
  )
  parser.add_argument(
    "--run-name",
    default=None,
    help="Shortcut: write logs/runs/<name>.jsonl (overridden by --log)",
  )
  parser.add_argument(
    "--opinion-leaders",
    type=int,
    default=int(os.getenv("ZUNDA_OPINION_LEADERS", str(DEFAULT_OPINION_LEADER_COUNT))),
    help="Opinion leaders on abnormal months (0=legacy crowd-only; default 5)",
  )
  parser.add_argument(
    "--opinion-parallel",
    action="store_true",
    default=_envBool("ZUNDA_OPINION_PARALLEL", True),
    help="Call opinion leaders in parallel (default on; LM Studio may serialize)",
  )
  parser.add_argument(
    "--agri-llm",
    dest="agriLlm",
    action="store_true",
    default=None,
    help="Force agri/logistics LLM (default: follow --llm)",
  )
  parser.add_argument(
    "--no-agri-llm",
    dest="agriLlm",
    action="store_false",
    help="Rule+CSV agri agents even if --llm",
  )
  parser.add_argument(
    "--agri-parallel",
    action="store_true",
    default=_envBool("ZUNDA_AGRI_PARALLEL", True),
    help="Parallel agri/logistics LLM workers (default on)",
  )
  parser.add_argument("--seed", type=int, default=42)
  return parser


def main(argv: list[str] | None = None) -> int:
  args = buildParser().parse_args(argv)
  if args.probe:
    from src.llm_client import probeModels

    print(json.dumps(probeModels(), ensure_ascii=False, indent=2))
    return 0

  if args.validate_baseline:
    import subprocess

    return subprocess.call([sys.executable, str(WORKSPACE / "scripts" / "validate_baseline.py")])

  logPath: Path | None = None
  if args.log:
    logPath = Path(args.log)
    if not logPath.is_absolute():
      logPath = WORKSPACE / logPath
  elif args.run_name:
    runDir = WORKSPACE / "logs" / "runs" / args.run_name
    runDir.mkdir(parents=True, exist_ok=True)
    logPath = runDir / "monthly.jsonl"

  followRegimes = args.standard == "historical"
  engineStandard = "edo_metal" if followRegimes else args.standard
  historicalPolicy = args.historical_policy or (followRegimes and not args.useLlm)
  print(
    f"Start standard={args.standard} engine={engineStandard} followRegimes={followRegimes} "
    f"range={args.start}..{args.end} "
    f"llm={args.useLlm} resume={args.resume} historicalPolicy={historicalPolicy} "
    f"opinionLeaders={args.opinion_leaders} opinionParallel={args.opinion_parallel} "
    f"agriLlm={args.agriLlm} agriParallel={args.agri_parallel} "
    f"log={logPath or 'logs/monthly_run.jsonl'}",
    flush=True,
  )
  runMonthlySimulation(
    standard=engineStandard,
    start=args.start,
    end=args.end,
    useLlm=args.useLlm,
    resume=args.resume,
    historicalPolicy=historicalPolicy,
    logPath=logPath,
    seed=args.seed,
    opinionLeaderCount=args.opinion_leaders,
    opinionParallel=args.opinion_parallel,
    agriLlm=args.agriLlm,
    agriParallel=args.agri_parallel,
    followRegimes=followRegimes,
  )
  return 0


if __name__ == "__main__":
  sys.exit(main())
