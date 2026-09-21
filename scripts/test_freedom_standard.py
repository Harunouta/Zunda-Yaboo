"""Unit tests for Freedom standard switching (no live LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gateway"))

from split import mergeRulerParts, prosePrompt  # noqa: E402

from src.economy import EconomyState, MonetaryStandard  # noqa: E402
from src.freedom_standard import (  # noqa: E402
  FREEDOM_PROMPT_MARKER,
  applyFreedomSwitch,
  parseFreedomStandard,
)
from src.law_and_policy import parseRulerDecision  # noqa: E402


def assertTrue(condition: bool, message: str) -> None:
  if not condition:
    raise AssertionError(message)


def testParseNextStandard() -> None:
  ok = parseRulerDecision(
    {
      "law": {
        "decree": "試す",
        "targetItem": "zundaNotes",
        "taxRate": 0.1,
        "penalty": "fine",
        "enforcementBudget": 10,
      },
      "policy": {"processBeansRatio": 0.5},
      "nextStandard": "anko",
    }
  )
  assertTrue(ok.nextStandard == "anko", "anko should parse")
  bad = parseRulerDecision(
    {
      "law": {
        "decree": "試す",
        "targetItem": "zundaNotes",
        "taxRate": 0.1,
        "penalty": "fine",
        "enforcementBudget": 10,
      },
      "policy": {"processBeansRatio": 0.5},
      "nextStandard": "yen_float",
    }
  )
  assertTrue(bad.nextStandard == "", "yen_float must be rejected")
  assertTrue(parseFreedomStandard("") is None, "empty is none")
  assertTrue(parseFreedomStandard("EDO_METAL") == MonetaryStandard.EDO_METAL, "case fold")


def testApplyFreedomSwitchAndCooldown() -> None:
  economy = EconomyState(year=1853, month=1, monetaryStandard=MonetaryStandard.ZUNDA)
  label, lastYm = applyFreedomSwitch(
    economy,
    requested=MonetaryStandard.ANKO,
    yearMonth="1853-01",
    lastSwitchYm=None,
  )
  assertTrue(label == "freedom:zunda->anko", f"label={label}")
  assertTrue(economy.monetaryStandard == MonetaryStandard.ANKO, "standard changed")
  assertTrue(lastYm == "1853-01", "last ym set")
  blocked, stillLast = applyFreedomSwitch(
    economy,
    requested=MonetaryStandard.AZUKI,
    yearMonth="1853-06",
    lastSwitchYm=lastYm,
  )
  assertTrue(blocked is None, "cooldown should block")
  assertTrue(economy.monetaryStandard == MonetaryStandard.ANKO, "unchanged during cooldown")
  assertTrue(stillLast == "1853-01", "last ym unchanged")
  allowed, newLast = applyFreedomSwitch(
    economy,
    requested=MonetaryStandard.AZUKI,
    yearMonth="1854-02",
    lastSwitchYm=lastYm,
  )
  assertTrue(allowed == "freedom:anko->azuki", f"after cooldown label={allowed}")
  assertTrue(economy.monetaryStandard == MonetaryStandard.AZUKI, "switched after cooldown")
  assertTrue(newLast == "1854-02", "last ym advanced")


def testGatewayMergeNextStandard() -> None:
  merged = mergeRulerParts(
    {"policy": {"processBeansRatio": 0.5}, "lawNumbers": {"taxRate": 0.1}},
    {"historicalPolicyIds": []},
    {"decree": "切替", "rulerReason": "行き詰まった", "nextStandard": "edo_metal"},
  )
  assertTrue(merged.get("nextStandard") == "edo_metal", "merge must keep nextStandard")
  sysPrompt, _ = prosePrompt(f"Month 1853-01. {FREEDOM_PROMPT_MARKER}: optional")
  assertTrue("nextStandard" in sysPrompt, "freedom prose prompt mentions nextStandard")


def main() -> int:
  testParseNextStandard()
  testApplyFreedomSwitchAndCooldown()
  testGatewayMergeNextStandard()
  print("ok freedom_standard")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
