# Duel compare packs (MIT, public sample)

For [`/compare_duel.html`](../../../web/viewer/compare_duel.html) — **2-run overlap viewer** (opinion 5 + agri 12, **no mascot**).

## What ships in git

| File | Status |
|------|--------|
| `sample_zunda_1603_1604.zip` | Synthetic demo (2 years, fake lines) |
| `sample_azuki_1603_1604.zip` | Synthetic demo pair for UI smoke |

Real 1603–2026 spans stay **local** until a **`--no-llm --standard historical`** (or similar mascot-less) run is packed here.

## Zip contents

- `monthly.jsonl` — macro, prices, PPP, fidelity, events, **`opinionLeaders`**, **`agriLogistics`** (slim)
- `launch.json` — `pack: "duel_opinion_agri"`, standard, span

**Not included:** `crowd`, `behavior`, mascot speech, decree text, LLM debug.

## Build from a local run

```powershell
python scripts/pack_duel_compare_zip.py `
  --log logs/runs/<zunda-run>/monthly.jsonl `
  --out logs/compare_export/zunda_duel.zip `
  --end 2026-08 `
  --label "zunda"

python scripts/pack_duel_compare_zip.py `
  --log logs/runs/<azuki-run>/monthly.jsonl `
  --out logs/compare_export/azuki_duel.zip `
  --label "azuki"
```

Do **not** commit `logs/` exports. Copy only mascot-less / redistributable packs into this folder.

## Future public sample (planned)

After a **`--no-llm`** historical baseline pair (e.g. two standards, same events, no persona bibles):

```powershell
python scripts/pack_duel_compare_zip.py --log logs/runs/historical_zunda_1603_2026/monthly.jsonl `
  --out data/redistributable/duel_packs/historical_zunda_duel.zip
python scripts/build_duel_public_samples.py  # refresh synthetic smoke zips
```

Load: `http://127.0.0.1:8765/compare_duel.html` → select **two** zips.
