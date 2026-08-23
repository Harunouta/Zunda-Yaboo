"""Operator CUI: play, export, analyze, and canvas-embed from monthly JSONL.

Does not retune the simulation engine. Live short demos still omit historicalPolicy.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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

PYTHON = sys.executable
DEFAULT_DELAY_SEC = 0.35
DEFAULT_TAIL_MONTHS = 12
DEFAULT_LOG = ROOT / "logs" / "runs" / "historical_1603_2026.jsonl"


def startDockerViewer() -> int:
  print("Starting viewer in Docker (0.0.0.0:8765). Windows: http://127.0.0.1:8765/")
  subprocess.call(["docker", "start", "Zunda-Yaboo"], cwd=str(ROOT))
  code = subprocess.call(
    [
      "docker",
      "exec",
      "-d",
      "-e",
      "PYTHONPATH=/workspace",
      "-w",
      "/workspace",
      "Zunda-Yaboo",
      "python",
      "scripts/web_viewer_server.py",
      "--bind",
      "0.0.0.0",
      "--port",
      "8765",
    ],
    cwd=str(ROOT),
  )
  if code != 0:
    print("docker exec failed. First time: powershell -File scripts\\republish_viewer_port.ps1")
    return code
  try:
    import webbrowser

    webbrowser.open("http://127.0.0.1:8765/")
  except Exception:
    pass
  return 0


def runScript(scriptName: str, extra: list[str]) -> int:
  cmd = [PYTHON, str(ROOT / "scripts" / scriptName), *extra]
  print(">", " ".join(cmd), flush=True)
  return subprocess.call(cmd, cwd=str(ROOT))


def listPresets() -> None:
  print("Presets (replay JSONL under logs/runs/):")
  for name, path in PRESETS.items():
    mark = "ok" if path.exists() else "missing"
    print(f"  {name:18} [{mark}] {path}")


def listLogs(directory: Path) -> list[Path]:
  if not directory.exists():
    print(f"No directory {directory}")
    return []
  files = sorted(directory.glob("*.jsonl"))
  for index, path in enumerate(files, start=1):
    sizeMb = path.stat().st_size / (1024 * 1024)
    print(f"  {index:3}  {path.name:48}  {sizeMb:7.1f} MiB")
  return files


def prompt(text: str, default: str) -> str:
  raw = input(f"{text} [{default}]: ").strip()
  return raw or default


def interactiveMenu() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  os.environ.setdefault("PYTHONPATH", str(ROOT))
  os.environ.setdefault("PYTHONIOENCODING", "utf-8")

  while True:
    print()
    print("=" * 60)
    print("  Zunda-Yaboo operator CUI  (engine is read-only)")
    print("=" * 60)
    print("  1  list presets")
    print("  2  list logs/runs JSONL")
    print("  3  play ticker (preset or path)")
    print("  4  analyze run")
    print("  5  preview last months")
    print("  6  export speech / prices / PPP")
    print("  7  export canvas embed JSON")
    print("  8  print src.main command (does not start a long run)")
    print("  9  live short ticker (no historicalPolicy)")
    print("  v  local HTML viewer http://127.0.0.1:8765/ (blocks until Ctrl+C)")
    print("  0  quit")
    choice = input("choice: ").strip()
    if choice in ("0", "q", "quit", "exit"):
      return 0
    if choice == "1":
      listPresets()
      continue
    if choice == "2":
      listLogs(ROOT / "logs" / "runs")
      continue
    if choice == "3":
      listPresets()
      presetOrPath = prompt("preset name or JSONL path", "historical-full")
      delay = prompt("delay seconds", str(DEFAULT_DELAY_SEC))
      onlyEvents = prompt("only events? y/n", "y").lower().startswith("y")
      extra = ["--delay", delay]
      if onlyEvents:
        extra.append("--only-events")
      if presetOrPath in PRESETS:
        extra = ["--preset", presetOrPath, *extra]
      else:
        extra = ["--log", presetOrPath, *extra]
      code = runScript("play_run.py", extra)
      if code:
        return code
      continue
    if choice == "4":
      logPath = prompt("log path", str(DEFAULT_LOG))
      code = runScript("analyze_run.py", ["--log", logPath])
      if code:
        return code
      continue
    if choice == "5":
      logPath = prompt("log path", str(DEFAULT_LOG))
      tail = prompt("tail months", str(DEFAULT_TAIL_MONTHS))
      code = runScript("preview_month_log.py", ["--log", logPath, "--tail", tail])
      if code:
        return code
      continue
    if choice == "6":
      logPath = prompt("log path", str(DEFAULT_LOG))
      kind = prompt("export kind: speech / prices / ppp", "ppp")
      if kind == "speech":
        code = runScript("export_speech_log.py", ["--log", logPath, "--only-events"])
      elif kind == "prices":
        code = runScript("export_price_csv.py", ["--log", logPath])
      else:
        code = runScript("export_purchasing_power.py", ["--log", logPath])
      if code:
        return code
      continue
    if choice == "7":
      logPath = prompt("log path", str(DEFAULT_LOG))
      code = runScript("export_canvas_embed.py", ["--log", logPath])
      if code:
        return code
      continue
    if choice == "8":
      standard = prompt("standard", "historical")
      start = prompt("start YYYY-MM", "1853-01")
      end = prompt("end YYYY-MM", "1853-12")
      useLlm = prompt("llm? y/n", "n").lower().startswith("y")
      llmFlag = "--llm" if useLlm else "--no-llm"
      hist = " --historical-policy" if standard in ("historical", "edo_metal") else ""
      print(
        f"python -m src.main {llmFlag} --standard {standard} "
        f"--start {start} --end {end}{hist}"
      )
      print("Long 1603-2026 LLM runs are optional; use --resume. This menu does not start them.")
      continue
    if choice == "9":
      print("Live demo omits historicalPolicy (short ticker only).")
      standard = prompt("standard", "zunda")
      start = prompt("start", "1853-01")
      end = prompt("end", "1853-12")
      extra = [
        "--live",
        "--standard",
        standard,
        "--start",
        start,
        "--end",
        end,
        "--delay",
        str(DEFAULT_DELAY_SEC),
      ]
      if prompt("llm? y/n", "n").lower().startswith("y"):
        extra.append("--llm")
      code = runScript("play_run.py", extra)
      if code:
        return code
      continue
    if choice in ("v", "V"):
      return startDockerViewer()
    print("unknown choice")


def main() -> int:
  parser = argparse.ArgumentParser(description="Operator CUI for replay and exports")
  parser.add_argument("--list-presets", action="store_true")
  parser.add_argument("--list-logs", action="store_true")
  parser.add_argument("--play-preset", default="", help="Non-interactive play")
  parser.add_argument("--only-events", action="store_true")
  parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SEC)
  parser.add_argument("--analyze", type=Path, default=None)
  parser.add_argument("--canvas-embed", type=Path, default=None)
  parser.add_argument("--serve-viewer", action="store_true", help="Local HTML viewer on 127.0.0.1:8765")
  args = parser.parse_args()

  if args.list_presets:
    listPresets()
    return 0
  if args.list_logs:
    listLogs(ROOT / "logs" / "runs")
    return 0
  if args.play_preset:
    extra = ["--preset", args.play_preset, "--delay", str(args.delay)]
    if args.only_events:
      extra.append("--only-events")
    return runScript("play_run.py", extra)
  if args.analyze is not None:
    return runScript("analyze_run.py", ["--log", str(args.analyze)])
  if args.canvas_embed is not None:
    return runScript("export_canvas_embed.py", ["--log", str(args.canvas_embed)])
  if args.serve_viewer:
    return startDockerViewer()
  return interactiveMenu()


if __name__ == "__main__":
  raise SystemExit(main())
