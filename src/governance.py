"""Political interference: proposed law/policy != effective outcome."""

from dataclasses import dataclass, field

from src.law_and_policy import (
  LawAct,
  PolicyPackage,
  RulerDecision,
  clipLawAct,
  clipPolicyPackage,
)


MAX_TAX_BY_EPOCH = {
  "E1": 0.50,
  "E2": 0.50,
  "E3": 0.60,
  "E4": 0.45,
}

CORRUPTION_BASE_BY_EPOCH = {
  "E1": 0.15,
  "E2": 0.12,
  "E3": 0.10,
  "E4": 0.08,
}

ENFORCEMENT_COST_PER_CAPITA = 0.002
LEGITIMACY_RIOT_THRESHOLD = 0.30
HIGH_TAX_THRESHOLD = 0.35


@dataclass
class EnginePolicy:
  taxRate: float = 0.1
  enforcementBudget: float = 20.0
  investSugarImport: float = 0.0
  processBeansRatio: float = 0.5


@dataclass
class GovernanceState:
  legitimacy: float = 0.7
  complianceRate: float = 0.85
  activeLaws: list[LawAct] = field(default_factory=list)


@dataclass
class EffectiveGovernance:
  law: LawAct
  policy: PolicyPackage
  enginePolicy: EnginePolicy
  effectiveTaxRate: float
  taxCollectionEfficiency: float
  reserveRelease: float
  detectionRate: float
  complianceRate: float
  legitimacy: float
  clippedFields: list[str] = field(default_factory=list)
  warnings: list[str] = field(default_factory=list)


def estimateCompliance(law: LawAct, legitimacy: float, foodBuffer: float, population: float) -> float:
  foodPerCapita = foodBuffer / max(population, 1.0)
  compliance = legitimacy * 0.6 + 0.25
  if law.taxRate > HIGH_TAX_THRESHOLD:
    compliance -= (law.taxRate - HIGH_TAX_THRESHOLD) * 0.8
  if foodPerCapita < 0.05:
    compliance -= 0.15
  if law.penalty == "confiscate_all":
    compliance -= 0.05
  return max(min(compliance, 0.98), 0.05)


def computeEnforcementEfficiency(law: LawAct, policy: PolicyPackage, population: float) -> float:
  budget = law.enforcementBudget * policy.enforcementPriority
  budget += policy.blackMarketCrackdown * law.enforcementBudget * 0.5
  needed = population * ENFORCEMENT_COST_PER_CAPITA
  if needed <= 0:
    return 1.0
  return max(min(budget / needed, 1.0), 0.05)


def computeDetectionRate(law: LawAct, policy: PolicyPackage, population: float) -> float:
  efficiency = computeEnforcementEfficiency(law, policy, population)
  base = law.enforcementBudget / max(population * 0.01, 1.0)
  boosted = base * policy.enforcementPriority * (1.0 + policy.blackMarketCrackdown)
  return max(min(boosted * efficiency, 0.95), 0.05)


def tickActiveLaws(governance: GovernanceState) -> GovernanceState:
  remaining: list[LawAct] = []
  for law in governance.activeLaws:
    law.durationTurns -= 1
    if law.durationTurns > 0:
      remaining.append(law)
  governance.activeLaws = remaining
  return governance


def registerLaw(governance: GovernanceState, law: LawAct) -> GovernanceState:
  if not law.lawId:
    law.lawId = f"law_{law.targetItem}_{law.taxRate}"
  governance.activeLaws.append(law)
  return governance


def applyGovernance(
  decision: RulerDecision,
  governance: GovernanceState,
  epoch: str,
  population: float,
  foodBuffer: float,
  processedReserve: float,
  events: list[str] | None = None,
) -> EffectiveGovernance:
  events = events or []
  maxTax = MAX_TAX_BY_EPOCH.get(epoch, 0.45)
  clippedFields: list[str] = []

  law, lawClips = clipLawAct(decision.law, maxTax)
  policy, policyClips = clipPolicyPackage(decision.policy)
  clippedFields.extend(lawClips + policyClips)

  compliance = estimateCompliance(law, governance.legitimacy, foodBuffer, population)
  enforcementEff = computeEnforcementEfficiency(law, policy, population)
  corruption = CORRUPTION_BASE_BY_EPOCH.get(epoch, 0.1)
  bureaucracyFactor = max(min(policy.bureaucracyEfficiency, 1.5), 0.3)
  taxCollectionEfficiency = compliance * enforcementEff * (1.0 - corruption) * bureaucracyFactor
  effectiveTaxRate = law.taxRate * taxCollectionEfficiency

  releaseRatio = policy.reserveReleaseRatio * bureaucracyFactor
  reserveRelease = min(processedReserve * releaseRatio, processedReserve * 0.5)
  detectionRate = computeDetectionRate(law, policy, population)

  warnings: list[str] = []
  if law.taxRate > 0.4 and compliance < 0.5:
    warnings.append("high_tax_low_compliance")
  if governance.legitimacy < LEGITIMACY_RIOT_THRESHOLD:
    warnings.append("riot_risk")
  if law.enforcementBudget > 0 and detectionRate < 0.15:
    warnings.append("law_without_teeth")

  enginePolicy = EnginePolicy(
    taxRate=law.taxRate,
    enforcementBudget=law.enforcementBudget,
    investSugarImport=policy.investSugarImport + policy.sugarSubsidy * 10,
    processBeansRatio=policy.processBeansRatio,
  )

  return EffectiveGovernance(
    law=law,
    policy=policy,
    enginePolicy=enginePolicy,
    effectiveTaxRate=effectiveTaxRate,
    taxCollectionEfficiency=taxCollectionEfficiency,
    reserveRelease=reserveRelease,
    detectionRate=detectionRate,
    complianceRate=compliance,
    legitimacy=governance.legitimacy,
    clippedFields=clippedFields,
    warnings=warnings,
  )


def updateLegitimacy(
  governance: GovernanceState,
  law: LawAct,
  starvationDeaths: float,
  foodBuffer: float,
  population: float,
  reserveReleased: float,
  crowdAnger: float = 0.0,
) -> GovernanceState:
  legitimacy = governance.legitimacy
  if starvationDeaths > 0:
    legitimacy -= min(starvationDeaths / max(population, 1.0), 0.08)
  foodPerCapita = foodBuffer / max(population, 1.0)
  if law.taxRate > HIGH_TAX_THRESHOLD and foodPerCapita < 0.08:
    legitimacy -= 0.03
  if reserveReleased > 0:
    legitimacy += 0.02
  legitimacy -= crowdAnger * 0.05
  legitimacy = max(min(legitimacy, 1.0), 0.05)
  governance.legitimacy = legitimacy
  governance.complianceRate = estimateCompliance(law, legitimacy, foodBuffer, population)
  return governance
