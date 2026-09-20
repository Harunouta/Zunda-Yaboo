"""Sparse interest-rate anchors for LLM-readable monthly logs.

Kinds change by era: Edo private lending samples, BOJ discount, call proxies.
Not a continuous policy-rate series from 1603.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
ANCHOR_PATH = WORKSPACE / "data" / "economy" / "interest_rate_anchors.csv"


def _toOrdinal(year: int, month: int) -> int:
  return year * 12 + (month - 1)


@lru_cache(maxsize=1)
def loadInterestAnchors() -> list[tuple[int, float, str, str, str]]:
  if not ANCHOR_PATH.is_file():
    return []
  rows: list[tuple[int, float, str, str, str]] = []
  with ANCHOR_PATH.open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
      try:
        year = int(row["year"])
        month = int(row.get("month") or 1)
        annualPct = float(row["annualPct"])
        kind = str(row.get("kind") or "unknown")
        evidence = str(row.get("evidence") or "")
        note = str(row.get("note") or "")
        rows.append((_toOrdinal(year, month), annualPct, kind, evidence, note))
      except (KeyError, TypeError, ValueError):
        continue
  rows.sort(key=lambda item: item[0])
  return rows


def interestRateForMonth(year: int, month: int) -> dict[str, Any]:
  anchors = loadInterestAnchors()
  if not anchors:
    return {
      "policyRateAnnualPct": None,
      "policyRateKind": "none",
      "evidence": "missing",
      "note": "no interest_rate_anchors.csv",
    }
  ordinal = _toOrdinal(year, month)
  if ordinal <= anchors[0][0]:
    _, pct, kind, evidence, note = anchors[0]
    return {
      "policyRateAnnualPct": round(pct, 4),
      "policyRateKind": kind,
      "evidence": evidence,
      "note": note,
    }
  if ordinal >= anchors[-1][0]:
    _, pct, kind, evidence, note = anchors[-1]
    return {
      "policyRateAnnualPct": round(pct, 4),
      "policyRateKind": kind,
      "evidence": evidence,
      "note": note,
    }
  for index in range(1, len(anchors)):
    left = anchors[index - 1]
    right = anchors[index]
    if left[0] <= ordinal <= right[0]:
      span = max(right[0] - left[0], 1)
      t = (ordinal - left[0]) / span
      pct = left[1] + (right[1] - left[1]) * t
      kind = right[2] if t > 0.5 else left[2]
      evidence = "inferred_interp" if left[0] != right[0] else left[3]
      note = right[4] if t > 0.5 else left[4]
      return {
        "policyRateAnnualPct": round(pct, 4),
        "policyRateKind": kind,
        "evidence": evidence,
        "note": note,
      }
  _, pct, kind, evidence, note = anchors[-1]
  return {
    "policyRateAnnualPct": round(pct, 4),
    "policyRateKind": kind,
    "evidence": evidence,
    "note": note,
  }


def creditCostNudge(annualPct: float | None) -> float:
  """Map annual % into a small [0,1] credit-cost nudge for mediators."""
  if annualPct is None:
    return 0.0
  # 0% -> 0, 10% -> ~0.2, clipped
  return max(0.0, min(0.35, float(annualPct) * 0.02))
