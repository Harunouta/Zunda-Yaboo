"""Monthly simulation engine: 1603-01 .. 2026-08 with optional LLM each month."""

import json
import os
from pathlib import Path
from typing import Any

from src.checkpoint import loadCheckpoint, saveCheckpoint
from src.commodity_watch import updateCommodityWatch
from src.crowd_mood import buildBehaviorLog, dryRunCrowd, summarizePolicy
from src.economy import (
  EconomyState,
  MonetaryStandard,
  advanceMonth,
  climateForMonth,
  getEpoch,
  reserveBase,
  simulateMonth,
)
from src.events import (
  EVENT_TABLE,
  FAMINE_EVENT_PREFIXES,
  buildCrowdPrompt,
  buildLeaderPrompt,
  eventsIncludeAnyPrefix,
  eventsWarrantDisasterRelief,
  eventsWarrantEpidemicPolicy,
  getEventPayload,
  getEventsForMonth,
  isAbnormalMonth,
)
from src.governance import (
  GovernanceState,
  applyGovernance,
  registerLaw,
  tickActiveLaws,
  updateLegitimacy,
)
from src.historical_track import (
  getHistoricalTarget,
  historicalPolicyForMonth,
  scoreHistoricalFidelity,
)
from src.law_and_policy import LawAct, PolicyPackage, RulerDecision
from src.mediators import (
  applyEventPayloads,
  applyShockDict,
  decayMediators,
  ensureMediators,
  runAgricultureAndLogistics,
)
from src.agri_logistics_agents import (
  applyAgriLeaks,
  ensureAgriRoster,
  pairKey,
  resolveAgriLogistics,
)
from src.policy_items import (
  applyItemToKit,
  applyMintBrake,
  classifyKit,
  clampActivatedIds,
  dealPolicyHand,
  decayCoeffKit,
  emptyCoeffKit,
  itemShock,
)
from src.policies import applyPolicyTweaks, loadPolicyCatalog, policyTimingLabel
from src.opinion_agents import (
  DEFAULT_OPINION_LEADER_COUNT,
  applyOpinionEconomyEffects,
  applySimulatedRegionEffects,
  applySimulatedTaxPenalty,
  attachMascotToCrowd,
  buildRegionSnapshot,
  decayRosterInfluence,
  ensureRegions,
  ensureRoster,
  propagateCrowdFromOpinions,
  resolveOpinionLeaders,
  updateRegionFounding,
)
from src.purchasing_power import computePurchasingPower, foodYenPerCapita

# Verbose per-month prints (default quiet for long runs).
PRINT_EACH_MONTH = os.getenv("ZUNDA_QUIET", "1") != "1"


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_LOG = WORKSPACE / "logs" / "monthly_run.jsonl"
DEFAULT_CHECKPOINT = WORKSPACE / "checkpoints" / "latest.json"
DEFAULT_ANOMALY = WORKSPACE / "logs" / "anomaly_months.json"

# Anomaly export policy (v2): flag a small minority of crisis / shock months.
# Governance warnings embedded in log "events" are NOT auto-flagged.
POPULATION_DROP_THRESHOLD = 30.0
FOOD_DROP_THRESHOLD = 250.0
RIOT_RISK_THRESHOLD = 0.35
CURRENCY_ABS_FLOOR = 0.15
# Absolute notesValueRatio floor is noisy during commodity bootstrap (1603–1620).
# Apply it only from this calendar year onward; MoM relative drops still apply earlier.
CURRENCY_ABS_FLOOR_MIN_YEAR = 1621
CURRENCY_REL_DROP_THRESHOLD = 0.25
FIDELITY_DROP_THRESHOLD = 0.05
PRICE_SHOCK_MIN_REL = 0.15
PRICE_SHOCK_MIN_ABS = 0.05
PRICE_SHOCK_PERCENTILE = 0.99
COMMODITY_STANDARDS = {"zunda", "anko", "azuki"}
POP_CATCHUP_RATE = 0.04
STARVE_CATCHUP_SCALE = 0.35
NEW_MOUTH_FOOD = 2.5
LEGIT_CATCHUP_RATE = 0.22
GOLD_SILVER_CATCHUP_RATE = 0.04
HISTORY_STANDARDS = {
  MonetaryStandard.EDO_METAL,
  MonetaryStandard.GOLD_YEN,
  MonetaryStandard.DOLLAR,
}


def defaultDecision(standard: MonetaryStandard, year: int, month: int, events: list[str]) -> RulerDecision:
  if standard == MonetaryStandard.ZUNDA:
    target = "zundaNotes"
  elif standard == MonetaryStandard.ANKO:
    target = "ankoNotes"
  elif standard == MonetaryStandard.AZUKI:
    target = "azukiNotes"
  elif standard == MonetaryStandard.DOLLAR:
    target = "dollarNotes"
  else:
    target = "rice"

  decree = "月次の年貢・通貨管理を行う"
  taxRate = 0.12
  processRatio = 0.45
  reserve = 0.0
  penalty = "confiscate_partial"
  hanIssue = 0.0
  activated: list[str] = []

  if eventsIncludeAnyPrefix(events, FAMINE_EVENT_PREFIXES):
    decree = "飢饉対策：備蓄放出と厳罰を併用するのだ"
    taxRate = 0.08
    reserve = 0.2
    penalty = "confiscate_all"
    processRatio = 0.6
    activated = ["okumai_relief"]
  elif eventsWarrantEpidemicPolicy(events):
    decree = "疫病流行：往来を抑え、救恤と埋葬を急ぐのだ"
    taxRate = 0.09
    reserve = 0.12
    penalty = "confiscate_partial"
  elif eventsWarrantDisasterRelief(events):
    decree = "災害対策：備蓄放出と救済を急ぐのだ"
    taxRate = 0.08
    reserve = 0.18
    penalty = "confiscate_partial"
    processRatio = 0.55
    activated = ["okumai_relief"]
  if "perry_arrival" in events:
    decree = "黒船来航：開国か抗戦か、砂糖と安全保障を交渉するのだ"
    taxRate = 0.1
  if "war_end" in events or "postwar" in events:
    decree = "戦後混乱の抑制と配給優先"
    reserve = 0.25
    taxRate = 0.05
  if "haihan_chiken" in events:
    decree = "藩札整理と新貨幣移行"
    hanIssue = 0.0
  if year >= 1868:
    processRatio = 0.65
    taxRate = min(taxRate, 0.14)
  if standard == MonetaryStandard.DOLLAR:
    tradeOpen = year >= 1949
    return RulerDecision(
      law=LawAct(
        decree=decree if events else "ドル建て財政と輸入の月次管理",
        targetItem=target,
        taxRate=min(taxRate, 0.18) if year >= 1949 else taxRate,
        penalty=penalty,
        enforcementBudget=25.0,
        durationTurns=1,
      ),
      policy=PolicyPackage(
        processBeansRatio=processRatio,
        reserveReleaseRatio=reserve,
        investSugarImport=12.0 if year >= 1949 else (5.0 if year >= 1853 else 0.0),
        tradeStance="open" if tradeOpen else "closed",
        hanSatsuIssueRatio=hanIssue,
        goldSilverTargetRatio=1.0,
        blackMarketCrackdown=0.15 if events else 0.0,
      ),
      activatedPolicyIds=activated,
    )

  return RulerDecision(
    law=LawAct(
      decree=decree,
      targetItem=target,
      taxRate=taxRate,
      penalty=penalty,
      enforcementBudget=25.0,
      durationTurns=1,
    ),
    policy=PolicyPackage(
      processBeansRatio=processRatio,
      reserveReleaseRatio=reserve,
      investSugarImport=5.0 if year >= 1853 else 0.0,
      tradeStance="open" if year >= 1858 else "closed",
      hanSatsuIssueRatio=hanIssue,
      goldSilverTargetRatio=1.0,
      blackMarketCrackdown=0.15 if events else 0.0,
    ),
    activatedPolicyIds=activated,
  )


def decisionFromHistorical(year: int, month: int) -> RulerDecision:
  hist = historicalPolicyForMonth(year, month)
  return RulerDecision(
    law=LawAct(
      decree=f"史実追従政策（{getHistoricalTarget(year, month).notes}）",
      targetItem="rice",
      taxRate=float(hist["taxRate"]),
      penalty="confiscate_partial",
      enforcementBudget=float(hist["enforcementBudget"]),
      durationTurns=1,
    ),
    policy=PolicyPackage(
      processBeansRatio=float(hist["processBeansRatio"]),
      reserveReleaseRatio=float(hist["reserveReleaseRatio"]),
      investSugarImport=float(hist["investSugarImport"]),
      tradeStance=str(hist["tradeStance"]),
      hanSatsuIssueRatio=float(hist["hanSatsuIssueRatio"]),
      goldSilverTargetRatio=float(hist["goldSilverTargetRatio"]),
    ),
  )


def resolveRuler(
  fallback: RulerDecision,
  prompt: str,
  useLlm: bool,
) -> tuple[RulerDecision, str, str]:
  if not useLlm:
    return fallback, "dry_run", ""
  try:
    from src.llm_client import callRuler

    decision, meta = callRuler(prompt)
    decreeText = str(decision.law.decree or "").strip()
    if not decreeText or decreeText in (".", "..", "..."):
      decision.law.decree = fallback.law.decree
    return decision, "llm", str(meta.get("rulerReason", ""))
  except Exception as error:
    return fallback, f"llm_fallback:{error}", ""


def resolveCrowd(
  prompt: str,
  foodPerCapita: float,
  legitimacy: float,
  hasEvents: bool,
  useLlm: bool,
  standard: str = "zunda",
  yearMonth: str = "1603-01",
  decree: str = "",
  events: list[str] | None = None,
  policySummary: str = "",
  prices: dict[str, Any] | None = None,
) -> dict[str, Any]:
  from src.mascot import buildMascotUserPrompt, mascotForStandard

  mascotId = mascotForStandard(standard)
  eventList = events or []
  if not useLlm:
    return dryRunCrowd(
      foodPerCapita,
      legitimacy,
      hasEvents,
      standard=standard,
      yearMonth=yearMonth,
      decree=decree,
      events=eventList,
    )
  try:
    from src.llm_client import callCrowd

    mascotPrompt = prompt
    if mascotId is not None:
      mascotPrompt = buildMascotUserPrompt(
        yearMonth,
        eventList,
        foodPerCapita,
        legitimacy,
        decree,
        prices=prices,
        policySummary=policySummary,
      )
    mood = callCrowd(mascotPrompt, mascotId=mascotId)
    mood["source"] = "llm"
    return mood
  except Exception as error:
    mood = dryRunCrowd(
      foodPerCapita,
      legitimacy,
      hasEvents,
      standard=standard,
      yearMonth=yearMonth,
      decree=decree,
      events=eventList,
    )
    mood["source"] = f"llm_fallback:{error}"
    return mood


def parseYearMonth(text: str) -> tuple[int, int]:
  yearStr, monthStr = text.split("-")
  return int(yearStr), int(monthStr)


def yearMonthKey(year: int, month: int) -> str:
  return f"{year:04d}-{month:02d}"


def isBeforeOrEqual(year: int, month: int, endYear: int, endMonth: int) -> bool:
  return (year, month) <= (endYear, endMonth)


def percentileSorted(sortedValues: list[float], quantile: float) -> float:
  if not sortedValues:
    return 0.0
  clamped = max(0.0, min(1.0, quantile))
  index = int(round((len(sortedValues) - 1) * clamped))
  return sortedValues[index]


def primaryPrice(row: dict[str, Any]) -> float | None:
  prices = row.get("prices") or {}
  for key in ("ricePrice", "zundaPrice", "ankoPrice"):
    value = prices.get(key)
    if value is not None:
      return float(value)
  return None


def fidelityScore(row: dict[str, Any]) -> float | None:
  fidelity = row.get("historicalFidelity") or {}
  score = fidelity.get("score")
  if score is None:
    return None
  return float(score)


def collectPriceShockThreshold(rows: list[dict[str, Any]]) -> float:
  relativeMoves: list[float] = []
  for index in range(1, len(rows)):
    prevPrice = primaryPrice(rows[index - 1])
    currPrice = primaryPrice(rows[index])
    if prevPrice is None or currPrice is None:
      continue
    if abs(prevPrice) < 1e-9:
      continue
    relativeMoves.append(abs(currPrice - prevPrice) / abs(prevPrice))
  if not relativeMoves:
    return PRICE_SHOCK_MIN_REL
  runPercentile = percentileSorted(sorted(relativeMoves), PRICE_SHOCK_PERCENTILE)
  return max(PRICE_SHOCK_MIN_REL, runPercentile)


def collectAnomalyReasons(
  prev: dict[str, Any],
  curr: dict[str, Any],
  priceShockThreshold: float,
) -> list[str]:
  reasons: list[str] = []
  prevMacro = prev.get("macro") or {}
  currMacro = curr.get("macro") or {}
  standard = str(curr.get("monetaryStandard") or prev.get("monetaryStandard") or "")

  popDrop = float(prevMacro.get("population", 0.0)) - float(currMacro.get("population", 0.0))
  foodDrop = float(prevMacro.get("foodBuffer", 0.0)) - float(currMacro.get("foodBuffer", 0.0))
  prevNotes = float(prevMacro.get("notesValueRatio", 1.0))
  currNotes = float(currMacro.get("notesValueRatio", 1.0))
  notesRelDrop = (prevNotes - currNotes) / max(prevNotes, 1e-9)
  riotRisk = float((curr.get("crowd") or {}).get("riotRisk", 0.0) or 0.0)

  if popDrop > POPULATION_DROP_THRESHOLD:
    reasons.append("population_crash")
  if foodDrop > FOOD_DROP_THRESHOLD:
    reasons.append("food_crash")

  currencyCrisis = notesRelDrop >= CURRENCY_REL_DROP_THRESHOLD
  yearMonth = str(curr.get("yearMonth") or "")
  year = int(yearMonth.split("-", 1)[0]) if len(yearMonth) >= 4 and yearMonth[:4].isdigit() else 9999
  if (
    standard in COMMODITY_STANDARDS
    and year >= CURRENCY_ABS_FLOOR_MIN_YEAR
    and currNotes < CURRENCY_ABS_FLOOR
  ):
    currencyCrisis = True
  if currencyCrisis:
    reasons.append("currency_crisis")

  if riotRisk >= RIOT_RISK_THRESHOLD:
    reasons.append("riot_risk")

  prevFidelity = fidelityScore(prev)
  currFidelity = fidelityScore(curr)
  if (
    prevFidelity is not None
    and currFidelity is not None
    and (prevFidelity - currFidelity) >= FIDELITY_DROP_THRESHOLD
  ):
    reasons.append("fidelity_drop")

  prevPrice = primaryPrice(prev)
  currPrice = primaryPrice(curr)
  if prevPrice is not None and currPrice is not None and abs(prevPrice) >= 1e-9:
    priceRel = abs(currPrice - prevPrice) / abs(prevPrice)
    priceAbs = abs(currPrice - prevPrice)
    if priceRel >= priceShockThreshold and priceAbs >= PRICE_SHOCK_MIN_ABS:
      reasons.append("price_shock")

  # Only named historical events count; ignore governance warnings in events[].
  for eventId in curr.get("events") or []:
    if eventId in EVENT_TABLE:
      reasons.append(str(eventId))

  return list(dict.fromkeys(reasons))


def exportAnomalies(logPath: Path, outPath: Path) -> int:
  if not logPath.exists():
    outPath.write_text("[]", encoding="utf-8")
    return 0
  rows = [json.loads(line) for line in logPath.read_text(encoding="utf-8").splitlines() if line.strip()]
  priceShockThreshold = collectPriceShockThreshold(rows)
  anomalies: list[dict[str, Any]] = []
  for index in range(1, len(rows)):
    prev = rows[index - 1]
    curr = rows[index]
    reasons = collectAnomalyReasons(prev, curr, priceShockThreshold)
    if reasons:
      anomalies.append({
        "yearMonth": curr["yearMonth"],
        "reasons": reasons,
        "lawDecree": curr.get("law", {}).get("decree", ""),
        "crowdMood": curr.get("crowd", {}).get("moodText", ""),
        "mascotSpeech": curr.get("crowd", {}).get("mascotSpeech", ""),
      })
  outPath.parent.mkdir(parents=True, exist_ok=True)
  outPath.write_text(json.dumps(anomalies, ensure_ascii=False, indent=2), encoding="utf-8")
  return len(anomalies)


def runMonthlySimulation(
  standard: str = "zunda",
  start: str = "1603-01",
  end: str = "2026-08",
  useLlm: bool = True,
  resume: bool = False,
  historicalPolicy: bool = False,
  logPath: Path | None = None,
  checkpointPath: Path | None = None,
  anomalyPath: Path | None = None,
  seed: int = 42,
  opinionLeaderCount: int = DEFAULT_OPINION_LEADER_COUNT,
  opinionParallel: bool = False,
  agriLlm: bool | None = None,
  agriParallel: bool = True,
  followRegimes: bool = False,
) -> Path:
  del seed  # reserved for future RNG wiring
  logPath = logPath or DEFAULT_LOG
  checkpointPath = checkpointPath or DEFAULT_CHECKPOINT
  anomalyPath = anomalyPath or DEFAULT_ANOMALY
  logPath.parent.mkdir(parents=True, exist_ok=True)
  checkpointPath.parent.mkdir(parents=True, exist_ok=True)

  monetary = MonetaryStandard(standard)
  startYear, startMonth = parseYearMonth(start)
  endYear, endMonth = parseYearMonth(end)
  initialPopulation = 12000.0

  if resume and checkpointPath.exists():
    economy, governance, turn, meta = loadCheckpoint(checkpointPath)
    if "resumeFrom" not in meta:
      meta["resumeFrom"] = economy.yearMonth
  else:
    economy = EconomyState(year=startYear, month=startMonth, monetaryStandard=monetary)
    # Both sweets exist since bakufu founding (watchable markets).
    economy.processedZunda = 200.0
    economy.ankoReserve = 180.0
    if monetary == MonetaryStandard.ANKO:
      economy.sugarStock = 450.0
    if monetary == MonetaryStandard.AZUKI:
      economy.azukiStock = 220.0
      economy.azukiNotes = 80.0
    if monetary == MonetaryStandard.EDO_METAL:
      economy.foodBuffer = 2500.0
      economy.riceKoku = 1200.0
    if monetary == MonetaryStandard.DOLLAR:
      economy.foodBuffer = 2500.0
      economy.riceKoku = 1200.0
      economy.dollarNotes = 1200.0
      economy.dollarReserves = 900.0
      economy.sugarStock = 400.0
    governance = GovernanceState()
    turn = 0
    meta = {
      "standard": standard,
      "start": start,
      "end": end,
      "historicalPolicy": historicalPolicy,
    }
    logPath.write_text("", encoding="utf-8")

  agentRoster = ensureRoster(meta)
  ensureRegions(meta)
  ensureMediators(meta, economy.riceKoku)
  if not isinstance(meta.get("coeffKit"), dict):
    meta["coeffKit"] = emptyCoeffKit()
  agriRoster = ensureAgriRoster(meta)
  runAgriLlm = useLlm if agriLlm is None else agriLlm
  meta["opinionLeaderCount"] = opinionLeaderCount
  meta["opinionParallel"] = opinionParallel
  baselineFoodYen = meta.get("baselineFoodYen")
  if baselineFoodYen is not None:
    baselineFoodYen = float(baselineFoodYen)

  while isBeforeOrEqual(economy.year, economy.month, endYear, endMonth):
    governance = tickActiveLaws(governance)
    yearMonth = economy.yearMonth
    regimeChange = None
    if followRegimes:
      from src.monetary_regimes import applyRegimeSwitch

      regimeChange = applyRegimeSwitch(economy, yearMonth)
    liveStandard = economy.monetaryStandard
    events = getEventsForMonth(yearMonth)
    epoch = getEpoch(economy.year)
    mediatorState = ensureMediators(meta, economy.riceKoku)
    decayMediators(mediatorState)
    eventPayloads = [payload for eventId in events if (payload := getEventPayload(eventId))]
    applyEventPayloads(mediatorState, eventPayloads)

    eventDisaster = None
    for eventId in events:
      payload = getEventPayload(eventId)
      if payload and payload.disasterOverride is not None:
        eventDisaster = payload.disasterOverride if eventDisaster is None else min(eventDisaster, payload.disasterOverride)

    climateIndex, disasterMultiplier = climateForMonth(economy.year, economy.month, eventDisaster)
    economy.climateIndex = climateIndex
    climateSource = "procedural"
    try:
      from src.climate_series import lookupClimateSeries

      seriesRow = lookupClimateSeries(economy.year, economy.month)
      if seriesRow is not None:
        climateSource = f"series:{seriesRow.get('source', 'csv')}"
    except Exception:
      climateSource = "procedural"

    decayCoeffKit(meta["coeffKit"])
    policyHand = dealPolicyHand(yearMonth, mediatorState)
    if PRINT_EACH_MONTH:
      print(f"month {yearMonth} llm={useLlm} events={events}", flush=True)
    if historicalPolicy and liveStandard in HISTORY_STANDARDS:
      decision = decisionFromHistorical(economy.year, economy.month)
      decisionSource = "historical_policy"
      rulerReason = ""
    else:
      fallback = defaultDecision(liveStandard, economy.year, economy.month, events)
      leaderPrompt = buildLeaderPrompt(
        events,
        yearMonth,
        liveStandard.value,
        policyHand=policyHand,
        agriBrief=str(meta.get("lastAgriBrief") or ""),
      )
      decision, decisionSource, rulerReason = resolveRuler(fallback, leaderPrompt, useLlm=useLlm)
    leaderPrompt = buildLeaderPrompt(
      events,
      yearMonth,
      liveStandard.value,
      policyHand=policyHand,
      agriBrief=str(meta.get("lastAgriBrief") or ""),
    )
    if PRINT_EACH_MONTH:
      print(f"  ruler={decisionSource}", flush=True)

    catalog = loadPolicyCatalog()
    activatedIds = clampActivatedIds(list(dict.fromkeys(decision.activatedPolicyIds)), policyHand, catalog)
    for policyId in activatedIds:
      option = catalog.get(policyId)
      if option is None:
        continue
      kitId = classifyKit(option)
      decision.policy = applyPolicyTweaks(decision.policy, option)
      applyShockDict(mediatorState, itemShock(kitId, option))
      applyItemToKit(meta["coeffKit"], kitId)
    decision.policy = applyMintBrake(decision.policy, meta["coeffKit"])
    trustRepair = float(meta["coeffKit"].get("trustRepair") or 0.0)
    if trustRepair:
      mediatorState["national"]["fiatTrust"] = min(
        1.0,
        max(0.05, float(mediatorState["national"]["fiatTrust"]) + trustRepair * 0.2),
      )
    decision.activatedPolicyIds = activatedIds
    policyPlay = [
      {
        "policyId": policyId,
        "timing": policyTimingLabel(policyId, yearMonth),
        "kit": classifyKit(catalog[policyId]) if policyId in catalog else "neutral",
      }
      for policyId in activatedIds
    ]

    agriBlock = resolveAgriLogistics(
      agriRoster,
      mediatorState,
      meta["coeffKit"],
      yearMonth,
      events,
      str(decision.law.decree or ""),
      useLlm=runAgriLlm,
      parallel=agriParallel and runAgriLlm,
    )
    decision.policy.processBeansRatio = max(
      0.0,
      min(1.0, float(decision.policy.processBeansRatio) + float(agriBlock.get("processBeansNudge") or 0.0)),
    )
    meta["lastAgriBrief"] = " / ".join(agriBlock.get("rumors") or [])[:400]
    parsedCosts: dict[tuple[str, str], float] = {}
    parsedCaps: dict[tuple[str, str], float] = {}
    for key, value in (agriBlock.get("routeCosts") or {}).items():
      pair = pairKey(str(key))
      if pair:
        parsedCosts[pair] = float(value)
    for key, value in (agriBlock.get("routeCaps") or {}).items():
      pair = pairKey(str(key))
      if pair:
        parsedCaps[pair] = float(value)

    effective = applyGovernance(
      decision,
      governance,
      epoch,
      economy.population,
      economy.foodBuffer,
      reserveBase(economy),
      events,
    )
    regionState = buildRegionSnapshot(meta)
    applySimulatedTaxPenalty(effective, regionState)
    governance = registerLaw(governance, effective.law)

    foodPerCapita = economy.foodBuffer / max(economy.population, 1.0)
    policySummary = summarizePolicy(effective.policy.toDict())
    crowdPrompt = buildCrowdPrompt(
      events,
      yearMonth,
      foodPerCapita,
      governance.legitimacy,
      decree=effective.law.decree,
      policySummary=policySummary,
      agriRumors=str(meta.get("lastAgriBrief") or ""),
    )

    opinionBlock: dict[str, Any] = {"active": False, "trigger": [], "agents": []}
    useOpinionPath = opinionLeaderCount > 0 and (
      useLlm or isAbnormalMonth(events, disasterMultiplier)
    )
    if useOpinionPath:
      opinionBlock = resolveOpinionLeaders(
        agentRoster,
        events=events,
        disasterMultiplier=disasterMultiplier,
        yearMonth=yearMonth,
        foodPerCapita=foodPerCapita,
        legitimacy=governance.legitimacy,
        decree=effective.law.decree,
        useLlm=useLlm,
        leaderCount=opinionLeaderCount,
        parallel=opinionParallel,
      )
      crowd = propagateCrowdFromOpinions(
        opinionBlock.get("agents") or [],
        foodPerCapita,
        governance.legitimacy,
      )
      crowd = attachMascotToCrowd(
        crowd,
        standard=liveStandard.value,
        yearMonth=yearMonth,
        foodPerCapita=foodPerCapita,
        legitimacy=governance.legitimacy,
        events=events,
        decree=effective.law.decree,
        useLlm=useLlm,
      )
    else:
      opinionBlock["influenceDecay"] = decayRosterInfluence(agentRoster)
      crowd = resolveCrowd(
        crowdPrompt,
        foodPerCapita,
        governance.legitimacy,
        bool(events),
        useLlm=useLlm,
        standard=liveStandard.value,
        yearMonth=yearMonth,
        decree=effective.law.decree,
        events=events,
        policySummary=policySummary,
      )

    nationalMed = mediatorState["national"]
    crowd["hoarding"] = min(
      1.0,
      float(crowd.get("hoarding") or 0.0)
      + float(nationalMed["socialUnrest"]) * 0.35
      + (1.0 - float(nationalMed["fiatTrust"])) * 0.25,
    )
    priceDamp = float(meta["coeffKit"].get("priceDamp") or 0.0)
    if priceDamp > 0:
      crowd["hoarding"] = float(crowd["hoarding"]) * max(0.4, 1.0 - priceDamp)

    if PRINT_EACH_MONTH:
      print(
        f"  crowd={crowd.get('source')} mascot={crowd.get('mascotId')} "
        f"opinion={opinionBlock.get('active')} "
        f"speech={str(crowd.get('mascotSpeech', ''))[:40]}",
        flush=True,
      )

    monthResult = simulateMonth(
      economy,
      effective.enginePolicy,
      effective.effectiveTaxRate,
      effective.reserveRelease,
      disasterMultiplier,
      crowdHoarding=float(crowd.get("hoarding", 0.0)),
      hanSatsuIssueRatio=effective.policy.hanSatsuIssueRatio,
      goldSilverTargetRatio=effective.policy.goldSilverTargetRatio,
    )
    monthResult.events = list(dict.fromkeys(events + monthResult.events + effective.warnings))

    if historicalPolicy:
      histTarget = getHistoricalTarget(economy.year, economy.month)
      targetPop = initialPopulation * float(histTarget.populationIndex)
      starveScale = STARVE_CATCHUP_SCALE if monthResult.starvationDeaths > 0.0 else 1.0
      beforePop = economy.population
      economy.population += (targetPop - economy.population) * POP_CATCHUP_RATE * starveScale
      gained = economy.population - beforePop
      if gained > 0.0:
        economy.foodBuffer += gained * NEW_MOUTH_FOOD
      if liveStandard != MonetaryStandard.DOLLAR:
        economy.goldSilverRatio += (
          float(histTarget.goldSilverRatio) - economy.goldSilverRatio
        ) * GOLD_SILVER_CATCHUP_RATE


    areaAgents = agriBlock.get("areaAgents") or {}
    newRice, newFood, mediatorSnap = runAgricultureAndLogistics(
      mediatorState,
      economy.riceKoku,
      monthResult.riceHarvest,
      economy.foodBuffer,
      coeffKit=meta["coeffKit"],
      areaAgents=areaAgents,
      routeCosts=parsedCosts,
      routeCaps=parsedCaps,
    )
    economy.riceKoku = newRice
    economy.foodBuffer = newFood
    applyAgriLeaks(economy, float(agriBlock.get("blackMarketLeak") or 0.0))
    importShock = float(nationalMed["importCostShock"])
    if importShock > 0:
      economy.sugarStock = max(economy.sugarStock * (1.0 - importShock * 0.2), 0.0)

    # Semi-empirical event shocks (legacy direct hits, merged with mediators).
    eventPopShock = 0.0
    eventCropLoss = 0.0
    eventEpidemic = 0.0
    for eventId in events:
      payload = getEventPayload(eventId)
      if payload is None:
        continue
      eventPopShock = max(eventPopShock, float(payload.populationShock or 0.0))
      eventCropLoss = max(eventCropLoss, float(payload.cropLossExtra or 0.0))
      eventEpidemic = max(eventEpidemic, float(payload.epidemicSeverity or 0.0))
    shockRate = min(eventPopShock + eventEpidemic * 0.5, 0.05)
    if shockRate > 0.0:
      shockDeaths = economy.population * shockRate
      economy.population = max(economy.population - shockDeaths, 100.0)
      monthResult.starvationDeaths += shockDeaths
    spoilAlready = float(nationalMed["stockSpoilage"]) > 0.0
    if eventCropLoss > 0.0 and not spoilAlready:
      economy.foodBuffer = max(economy.foodBuffer * (1.0 - eventCropLoss * 0.25), 0.0)
      economy.riceKoku = max(economy.riceKoku * (1.0 - eventCropLoss), 0.0)
      economy.edamameStock = max(economy.edamameStock * (1.0 - eventCropLoss), 0.0)
      economy.azukiStock = max(economy.azukiStock * (1.0 - eventCropLoss), 0.0)
      economy.rawBeans = economy.edamameStock + economy.azukiStock

    # Apply world effects lightly
    if any(getEventPayload(e) and getEventPayload(e).worldEffect == "sugar_spike" for e in events):
      economy.sugarStock = max(economy.sugarStock - 20.0, 0.0)
    if any(getEventPayload(e) and getEventPayload(e).worldEffect == "gold_outflow" for e in events):
      economy.goldRyo *= 0.95
    if any(getEventPayload(e) and getEventPayload(e).worldEffect == "hyperinflation" for e in events):
      economy.zundaNotes *= 1.2
      economy.ankoNotes *= 1.2
      economy.azukiNotes *= 1.2
      economy.dollarNotes *= 1.2
      economy.hanSatsuCredit = max(economy.hanSatsuCredit * 0.8, 0.05)
    if any(getEventPayload(e) and getEventPayload(e).worldEffect == "oil_spike" for e in events):
      economy.sugarStock = max(economy.sugarStock * 0.92, 0.0)
      economy.foodBuffer = max(economy.foodBuffer * 0.97, 0.0)
      economy.dollarReserves = max(economy.dollarReserves * 0.94, 0.0)
    if any(getEventPayload(e) and getEventPayload(e).worldEffect == "han_satsu_crisis" for e in events):
      economy.hanSatsuCredit = max(economy.hanSatsuCredit * 0.55, 0.05)
    if any(getEventPayload(e) and getEventPayload(e).worldEffect == "chip_spike" for e in events):
      # Semiconductor / electronics shortage: industrial feedstock + logistics proxy.
      economy.sugarStock = max(economy.sugarStock * 0.94, 0.0)
      economy.foodBuffer = max(economy.foodBuffer * 0.985, 0.0)
      economy.zundaNotes *= 1.02
      economy.ankoNotes *= 1.02
      economy.azukiNotes *= 1.02

    opinionEconomy = {"fledPopulation": 0.0, "foodDrain": 0.0, "sugarDrain": 0.0}
    if opinionBlock.get("active"):
      opinionEconomy = applyOpinionEconomyEffects(
        economy,
        list(opinionBlock.get("agents") or []),
      )
    regionInfo = updateRegionFounding(meta, agentRoster, yearMonth)
    simulatedEffects = applySimulatedRegionEffects(
      economy,
      governance,
      regionInfo,
      drainLegitimacy=not historicalPolicy,
    )
    opinionBlock = {
      **opinionBlock,
      "economyEffects": opinionEconomy,
      "region": regionInfo,
      "simulatedEffects": simulatedEffects,
    }

    economy.foodBuffer = max(economy.foodBuffer * (1.0 - float(crowd.get("hoarding", 0.0)) * 0.02), 0.0)

    governance = updateLegitimacy(
      governance,
      effective.law,
      monthResult.starvationDeaths,
      economy.foodBuffer,
      economy.population,
      effective.reserveRelease,
      crowdAnger=float(crowd.get("anger", 0.0)),
    )
    if historicalPolicy:
      histTarget = getHistoricalTarget(economy.year, economy.month)
      governance.legitimacy += (float(histTarget.legitimacy) - governance.legitimacy) * LEGIT_CATCHUP_RATE
      governance.legitimacy = max(0.05, min(1.0, governance.legitimacy))

    prices = updateCommodityWatch(
      climateIndex=climateIndex,
      disasterMultiplier=disasterMultiplier,
      sugarStock=economy.sugarStock,
      processedZunda=economy.processedZunda,
      ankoReserve=economy.ankoReserve,
      riceKoku=economy.riceKoku,
      goldSilverRatio=economy.goldSilverRatio,
      crowdHoarding=float(crowd.get("hoarding", 0.0)),
      events=events,
      edamameStock=economy.edamameStock,
      azukiStock=economy.azukiStock,
      riceHarvest=monthResult.riceHarvest,
      edamameHarvest=monthResult.edamameHarvest,
      azukiHarvest=monthResult.azukiHarvest,
      dollarNotes=economy.dollarNotes,
      dollarReserves=economy.dollarReserves,
    )
    foodPerCapitaFinal = economy.foodBuffer / max(economy.population, 1.0)
    if baselineFoodYen is None:
      baselineFoodYen = foodYenPerCapita(foodPerCapitaFinal, economy.year)
      meta["baselineFoodYen"] = baselineFoodYen
    purchasingPower = computePurchasingPower(
      zundaPrice=prices.zundaPrice,
      ankoPrice=prices.ankoPrice,
      azukiPrice=prices.azukiPrice,
      ricePrice=prices.ricePrice,
      foodPerCapita=foodPerCapitaFinal,
      goldSilverRatio=economy.goldSilverRatio,
      baselineFoodYen=baselineFoodYen,
      dollarPrice=prices.dollarPrice,
      fxYenPerDollar=economy.fxYenPerDollar,
      year=economy.year,
    )
    histTarget = getHistoricalTarget(economy.year, economy.month)
    riceScarcityProxy = 1.0 / max(float(disasterMultiplier), 0.25)
    popIndex = economy.population / initialPopulation
    fidelity = scoreHistoricalFidelity(
      riceScarcityProxy,
      economy.goldSilverRatio,
      governance.legitimacy,
      popIndex,
      histTarget,
    )

    behavior = buildBehaviorLog(
      yearMonth=yearMonth,
      decree=effective.law.decree,
      decisionSource=decisionSource,
      policy=effective.policy.toDict(),
      crowd=crowd,
      events=events,
      foodPerCapita=foodPerCapita,
      legitimacy=governance.legitimacy,
      rulerReason=rulerReason,
    )

    logEntry = {
      "turn": turn,
      "yearMonth": yearMonth,
      "year": economy.year,
      "month": economy.month,
      "epoch": epoch,
      "monetaryStandard": liveStandard.value,
      "regimeChange": regimeChange,
      "macro": {
        "population": round(economy.population, 1),
        "foodBuffer": round(economy.foodBuffer, 1),
        "sugarStock": round(economy.sugarStock, 1),
        "notesValueRatio": round(monthResult.notesValueRatio, 3),
        "taxCollected": round(monthResult.taxCollected, 2),
        "spoiled": round(monthResult.spoiled, 2),
        "harvest": round(monthResult.harvest, 2),
        "riceHarvest": round(monthResult.riceHarvest, 2),
        "edamameHarvest": round(monthResult.edamameHarvest, 2),
        "azukiHarvest": round(monthResult.azukiHarvest, 2),
        "edamameStock": round(economy.edamameStock, 1),
        "azukiStock": round(economy.azukiStock, 1),
        "rawBeans": round(economy.rawBeans, 1),
        "zundaNotes": round(economy.zundaNotes, 1),
        "ankoNotes": round(economy.ankoNotes, 1),
        "azukiNotes": round(economy.azukiNotes, 1),
        "processedZunda": round(economy.processedZunda, 1),
        "ankoReserve": round(economy.ankoReserve, 1),
        "riceKoku": round(economy.riceKoku, 1),
        "goldRyo": round(economy.goldRyo, 1),
        "silverMonme": round(economy.silverMonme, 1),
        "hanSatsu": round(economy.hanSatsu, 1),
        "hanSatsuCredit": round(economy.hanSatsuCredit, 3),
        "goldSilverRatio": round(economy.goldSilverRatio, 3),
        "dollarNotes": round(economy.dollarNotes, 1),
        "dollarReserves": round(economy.dollarReserves, 1),
        "fxYenPerDollar": round(economy.fxYenPerDollar, 2),
      },
      "prices": prices.toDict(),
      "purchasingPower": purchasingPower.toDict(),
      "historicalFidelity": fidelity,
      "climate": {
        "index": round(climateIndex, 3),
        "disasterMultiplier": round(disasterMultiplier, 3),
        "source": climateSource,
        "riceHarvest": round(monthResult.riceHarvest, 2),
        "edamameHarvest": round(monthResult.edamameHarvest, 2),
        "azukiHarvest": round(monthResult.azukiHarvest, 2),
        "eventPopShock": round(eventPopShock, 4),
        "eventCropLoss": round(eventCropLoss, 4),
        "eventEpidemic": round(eventEpidemic, 4),
      },
      "law": effective.law.toDict(),
      "policy": effective.policy.toDict(),
      "activatedPolicyIds": activatedIds,
      "policyHand": [item.policyId for item in policyHand],
      "policyPlay": policyPlay,
      "mediators": mediatorSnap,
      "governance": {
        "legitimacy": round(governance.legitimacy, 3),
        "complianceRate": round(effective.complianceRate, 3),
        "proposedTaxRate": round(effective.law.taxRate, 3),
        "effectiveTaxRate": round(effective.effectiveTaxRate, 3),
        "clippedFields": effective.clippedFields,
        "regionMode": (opinionBlock.get("region") or {}).get("mode", "historical"),
      },
      "crowd": crowd,
      "behavior": behavior,
      "opinionLeaders": opinionBlock,
      "agriLogistics": {
        "source": agriBlock.get("source"),
        "processBeansNudge": agriBlock.get("processBeansNudge"),
        "blackMarketLeak": agriBlock.get("blackMarketLeak"),
        "rumors": agriBlock.get("rumors") or [],
        "agents": agriBlock.get("agents") or [],
      },
      "events": monthResult.events,
      "llm": {
        "decisionSource": decisionSource,
        "leaderPrompt": leaderPrompt,
        "crowdPrompt": crowdPrompt,
        "historicalPolicy": historicalPolicy,
        "rulerReason": behavior["rulerReason"],
      },
    }

    with logPath.open("a", encoding="utf-8") as handle:
      handle.write(json.dumps(logEntry, ensure_ascii=False) + "\n")

    nextYear, nextMonth = advanceMonth(economy.year, economy.month)
    economy.year = nextYear
    economy.month = nextMonth
    turn += 1

    meta["agents"] = agentRoster
    meta["agriRoster"] = agriRoster
    saveCheckpoint(
      checkpointPath,
      economy,
      governance,
      turn,
      meta={**meta, "lastCompleted": yearMonth, "useLlm": useLlm},
    )

    if turn % 12 == 0:
      print(
        f"[{yearMonth}] turn={turn} pop={economy.population:.0f} "
        f"zunda={prices.zundaPrice:.3f}(~¥{purchasingPower.zundaYen:.0f}) "
        f"anko={prices.ankoPrice:.3f}(~¥{purchasingPower.ankoYen:.0f}) "
        f"azuki={prices.azukiPrice:.3f}(~¥{purchasingPower.azukiYen:.0f}) "
        f"live={purchasingPower.livingVsModern*100:.2f}% "
        f"{purchasingPower.vibe} "
        f"fidelity={fidelity['score']:.3f} src={decisionSource}",
        flush=True,
      )

  exportAnomalies(logPath, anomalyPath)
  print(f"Done. log={logPath} checkpoint={checkpointPath} anomalies={anomalyPath}", flush=True)
  try:
    from src.life_recap import writeLifeRecap

    recap = writeLifeRecap(logPath, useLlm=useLlm)
    print(f"Life recap ({recap.get('source')}): {recap.get('title')}", flush=True)
  except Exception as error:
    print(f"Life recap skipped: {error}", flush=True)
  if os.getenv("ZUNDA_EXPORT_SPEECH", "0") == "1":
    import subprocess
    import sys

    subprocess.run(
      [sys.executable, str(WORKSPACE / "scripts" / "export_speech_log.py"), "--log", str(logPath)],
      check=False,
    )
  return logPath
