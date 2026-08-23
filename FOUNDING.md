# Founding / Simulated regions (Phase 2+)

## Behavior

1. On abnormal months, opinion leaders may `organize` (esp. cult / frontier in famine).
2. Each organize bumps `influence` by `ORGANIZE_INFLUENCE_DELTA` (0.04).
3. When founding-mode peak influence crosses each region's threshold, that region flips
   `historical` → `simulated`:
   - `edo_core` — threshold = `ZUNDA_FOUNDING_THRESHOLD` (default **0.18**), taxShare 0.55
   - `tohoku_rim` — slightly easier (threshold −0.04), taxShare 0.20
   - `osaka_hub` — slightly harder (threshold +0.04), taxShare 0.25
4. While any region is Simulated:
   - Tax/compliance penalty scales with **sum of taxShare** of Simulated regions
   - Food/legitimacy drain scales with **foodDrainScale** stack
5. Quiet months decay `influence` (`PEACE_INFLUENCE_DECAY` / slower if `founding`).
6. State persists in checkpoint `meta.regions`.

## Logs

- `governance.regionMode` (primary = edo_core)
- `opinionLeaders.region` (`regions`, `flippedRegionIds`, `simulatedTaxShare`, …)
- `opinionLeaders.simulatedEffects`

## Smoke

```powershell
python scripts/smoke_founding.py
python -m src.main --no-llm --standard zunda --start 1782-01 --end 1787-08 --opinion-leaders 5 --log logs/runs/tonight_multiregion_tenmei.jsonl
```

Example (multi-region dry-run): **1786-06** tohoku → **1786-08** edo (+tohoku).

## Not yet

- True “new nation” polity switch / separate treasuries
- Revert Simulated → Historical
