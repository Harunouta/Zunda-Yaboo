# Compare packs (MIT, original sim output)

Speechless monthly stats for the local HTML viewer (`/compare.html`).

| File | Span | Standard |
|------|------|----------|
| `historical_stats_1603_2026.zip` | 1603-01 .. 2026-08 | `historical` (metal → gold yen → dollar) |

Each zip contains only:

- `monthly.jsonl` — population, prices, purchasing power, fidelity, event notes
- `launch.json` — standard / span metadata

No `life_recap`, no mascot speech, no persona bibles.

Rebuild (does not write this folder by default):

```powershell
python scripts/pack_historical_compare_zip.py --log logs/runs/historical_1603_2026.jsonl --out data/redistributable/compare_packs/historical_stats_1603_2026.zip
```

Load in the viewer: `http://127.0.0.1:8765/compare.html` → choose the zip.
