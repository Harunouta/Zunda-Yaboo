"""Export monthly price columns from a JSONL run for spreadsheet / chart tools."""

import argparse
import csv
import json
from pathlib import Path


def exportPrices(logPath: Path, outPath: Path) -> int:
  rows: list[dict] = []
  for line in logPath.read_text(encoding="utf-8").splitlines():
    if not line.strip():
      continue
    entry = json.loads(line)
    prices = entry.get("prices") or {}
    fidelity = entry.get("historicalFidelity") or {}
    rows.append({
      "yearMonth": entry.get("yearMonth"),
      "standard": entry.get("monetaryStandard"),
      "zundaPrice": prices.get("zundaPrice"),
      "ankoPrice": prices.get("ankoPrice"),
      "ricePrice": prices.get("ricePrice"),
      "goldPrice": prices.get("goldPrice"),
      "silverPrice": prices.get("silverPrice"),
      "zundaVsAnko": prices.get("zundaVsAnko"),
      "zundaYen": (entry.get("purchasingPower") or {}).get("zundaYen"),
      "ankoYen": (entry.get("purchasingPower") or {}).get("ankoYen"),
      "foodYenPerCapita": (entry.get("purchasingPower") or {}).get("foodYenPerCapita"),
      "livingVsModern": (entry.get("purchasingPower") or {}).get("livingVsModern"),
      "developmentIndex": (entry.get("purchasingPower") or {}).get("developmentIndex"),
      "vibe": (entry.get("purchasingPower") or {}).get("vibe"),
      "fidelity": fidelity.get("score"),
      "population": (entry.get("macro") or {}).get("population"),
      "mascotId": (entry.get("crowd") or {}).get("mascotId"),
      "mascotSpeech": (entry.get("crowd") or {}).get("mascotSpeech"),
    })
  if not rows:
    raise SystemExit(f"No rows in {logPath}")
  outPath.parent.mkdir(parents=True, exist_ok=True)
  with outPath.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
  return len(rows)


def main() -> None:
  parser = argparse.ArgumentParser(description="Export Zunda-Yaboo prices to CSV")
  parser.add_argument(
    "--log",
    default="logs/baseline_edo_metal_hist.jsonl",
    help="Input monthly JSONL",
  )
  parser.add_argument(
    "--out",
    default="logs/prices_export.csv",
    help="Output CSV path",
  )
  args = parser.parse_args()
  root = Path(__file__).resolve().parents[1]
  logPath = root / args.log if not Path(args.log).is_absolute() else Path(args.log)
  outPath = root / args.out if not Path(args.out).is_absolute() else Path(args.out)
  count = exportPrices(logPath, outPath)
  print(f"Wrote {count} rows to {outPath}")


if __name__ == "__main__":
  main()
