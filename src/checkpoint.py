"""Checkpoint save/load for long monthly runs (1603-01 .. 2026-08)."""

import json
from pathlib import Path
from typing import Any

from src.economy import EconomyState
from src.governance import GovernanceState
from src.law_and_policy import LawAct


def saveCheckpoint(
  path: Path,
  economy: EconomyState,
  governance: GovernanceState,
  turn: int,
  meta: dict[str, Any] | None = None,
) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  payload = {
    "turn": turn,
    "economy": economy.toDict(),
    "governance": {
      "legitimacy": governance.legitimacy,
      "complianceRate": governance.complianceRate,
      "activeLaws": [law.toDict() for law in governance.activeLaws],
    },
    "meta": meta or {},
  }
  path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def loadCheckpoint(path: Path) -> tuple[EconomyState, GovernanceState, int, dict[str, Any]]:
  payload = json.loads(path.read_text(encoding="utf-8"))
  economy = EconomyState.fromDict(payload["economy"])
  govRaw = payload["governance"]
  governance = GovernanceState(
    legitimacy=float(govRaw.get("legitimacy", 0.7)),
    complianceRate=float(govRaw.get("complianceRate", 0.85)),
    activeLaws=[
      LawAct(
        decree=item.get("decree", ""),
        targetItem=item.get("targetItem", "zundaNotes"),
        taxRate=float(item.get("taxRate", 0.1)),
        penalty=item.get("penalty", "confiscate_partial"),
        enforcementBudget=float(item.get("enforcementBudget", 20)),
        lawId=item.get("lawId", ""),
        durationTurns=int(item.get("durationTurns", 1)),
      )
      for item in govRaw.get("activeLaws", [])
    ],
  )
  return economy, governance, int(payload.get("turn", 0)), payload.get("meta", {})
