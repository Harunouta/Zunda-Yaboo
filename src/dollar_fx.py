"""Illustrative JPY per USD series for the dollar monetary standard.

Anchors live in data/economy/fx_jpy_per_usd.csv (see provenance.csv).
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
FX_PATH = WORKSPACE / "data" / "economy" / "fx_jpy_per_usd.csv"


@lru_cache(maxsize=1)
def loadFxAnchors() -> list[tuple[int, int, float]]:
  rows: list[tuple[int, int, float]] = []
  with FX_PATH.open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
      rows.append((int(row["year"]), int(row["month"]), float(row["jpyPerUsd"])))
  rows.sort(key=lambda item: (item[0], item[1]))
  return rows


def _ordinal(year: int, month: int) -> int:
  return year * 12 + (month - 1)


def fxYenPerDollar(year: int, month: int) -> float:
  anchors = loadFxAnchors()
  stamp = _ordinal(year, month)
  first = anchors[0]
  last = anchors[-1]
  if stamp <= _ordinal(first[0], first[1]):
    return first[2]
  if stamp >= _ordinal(last[0], last[1]):
    return last[2]
  for index in range(1, len(anchors)):
    left = anchors[index - 1]
    right = anchors[index]
    leftStamp = _ordinal(left[0], left[1])
    rightStamp = _ordinal(right[0], right[1])
    if leftStamp <= stamp <= rightStamp:
      span = max(rightStamp - leftStamp, 1)
      mix = (stamp - leftStamp) / span
      return left[2] + (right[2] - left[2]) * mix
  return last[2]
