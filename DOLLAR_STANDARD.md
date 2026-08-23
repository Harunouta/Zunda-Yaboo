# ドル本位制（実装のみ・現代価値の本チューニングは後）

CLI: `--standard dollar`

日本で現代を走るための第四の本位。実物（米・豆・食料）は `edo_metal` に近い収穫・消費。貨幣は `dollarNotes` / `dollarReserves`。円ドルは `src/dollar_fx.py` の折れ線（1949=360、プラザ以降、2020年代〜150円台）。

- マスコットなし（ずんだ／あんことは独立）
- `--historical-policy` は江戸金属専用のまま
- 飢饉係数の合わせ込みはしない（現代は飢饉が主戦場ではない）
- PPP: `purchasingPower.dollarYen` = `fxYenPerDollar × dollarPrice`

```powershell
python -m src.main --no-llm --standard dollar --start 2020-01 --end 2021-12 --opinion-leaders 0 --log logs/runs/smoke_dollar_2020_2021.jsonl
python scripts/smoke_dollar.py
```
