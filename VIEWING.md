# 見て遊ぶ（端末＋Canvas＋任意のローカル HTML）

本格公開 GUI はない。いまは端末＋Cursor Canvas＋**任意のローカル HTML**。契約は **[`docs/CUI_AND_VIZ.md`](docs/CUI_AND_VIZ.md)**。Canvas はチャット横の年次要約。月次セリフの展開と短い起動はブラウザ（`127.0.0.1` のみ）。

## 0. ローカル HTML（Docker で上げて Windows で見る）

コンテナ内 `127.0.0.1` は Windows から見えない。**コンテナは `0.0.0.0:8765`、ホストは `127.0.0.1:8765` だけ公開**する。

初回だけポートを付ける（pip 入りイメージを commit して作り直し）:

```powershell
powershell -File D:\Zunda-Yaboo\scripts\republish_viewer_port.ps1
```

あとは `open_viewer.bat` をダブルクリック。Docker 内で viewer が動き、Windows の既定ブラウザが `http://127.0.0.1:8765/` を開く。JSONL は `/workspace/logs/runs`（ホストと同じ bind）。短い sim はコンテナ内の `python -m src.main`。`--run-name` は `logs/runs/<名前>/monthly.jsonl`。画面の「AI / モデル」で LM Studio または OpenAI API と役ごとのモデルを保存できる（Cursor 不要）。実行中はぐるぐると推論中の年月。年次の布告・マスコット・世論は「その年を見る」。

## 1. セリフがパカパカ（〜2026含む）

操作入口（Docker なら `/workspace`）:

```powershell
python scripts/operator_cui.py
python scripts/operator_cui.py --list-presets
python scripts/export_canvas_embed.py --log logs/runs/historical_1603_2026.jsonl
```

```powershell
cd D:\Zunda-Yaboo
$env:PYTHONPATH = "D:\Zunda-Yaboo"
$env:PYTHONIOENCODING = "utf-8"

# 1603→2026 フル（静か月も全部・長い）
python scripts/play_run.py --preset full-zunda --delay 0.05

# イベント月だけ早送り（おすすめ）
python scripts/play_run.py --preset full-zunda --only-events --delay 0.35

# コロナ〜2026
python scripts/play_run.py --preset covid-modern --delay 0.4
python scripts/play_run.py --preset covid-modern --only-events --delay 0.5

# 天明＋飢饉＋建国（今夜ログ / PPP付き）
python scripts/play_run.py --preset tenmei --only-events --delay 0.35

python scripts/play_run.py --preset azuki-tenmei --delay 0.35
python scripts/play_run.py --preset azuki-1853 --delay 0.4

python scripts/play_run.py --preset historical-full --only-events --delay 0.2

# 1801→2026（世界史込み dry-run）
python scripts/play_run.py --preset world-modern --only-events --delay 0.4
```

Presets: `full-zunda` / `tenmei` / `covid-modern` / `perry` / `world-modern` / `floods-1950s` / `azuki-tenmei` / `azuki-1853` / `historical-full`

## 2. セリフ一覧ログを残す

```powershell
python scripts/export_speech_log.py --log logs/runs/overnight_b_llm_1853.jsonl
python scripts/export_speech_log.py --log logs/runs/founding_tenmei_1780_1790.jsonl --only-events
```

出力:
- `*.speech.md` … 読み物
- `*.speech.jsonl` … 機械用（ruler / mascot / opinion）

## 3. 価格CSV・折れ線

```powershell
python scripts/export_price_csv.py --log logs/runs/zunda_full_1603_2026.jsonl --out logs/runs/zunda_full_1603_2026_prices.csv
python scripts/analyze_run.py --log logs/runs/world_era_1801_2026.jsonl
```

Canvas（チャット横）: `zunda-price-worldera.canvas.tsx`（ずんだ価格の長期折れ線）

## 3b. 現代円で比較（米PPP）

「開幕は貧しい／天明で谷／近代以降は現代円の食費に近づく」。詳細は **`PURCHASING_POWER.md`**（時代バスケット×在庫。古い Canvas 文言は作り直し）。

```powershell
python scripts/export_purchasing_power.py --log logs/runs/zunda_full_1603_2026.jsonl
python scripts/export_purchasing_power.py --log logs/runs/edo_metal_hist_1603_1868.jsonl
```

- 月次: `*_ppp.csv` / 年次: `*_ppp_yearly.csv`
- Canvas: `zunda-purchasing-power.canvas.tsx`（食/人円・発展指数）
- `play_run` に `yen≈` 行（ずんだ¥ / あんこ¥ / vs今% / 感想）

## 4. 解析サマリ

```powershell
python scripts/analyze_run.py --log logs/runs/founding_tenmei_1780_1790.jsonl
python scripts/preview_month_log.py --log logs/runs/overnight_b_llm_1853.jsonl --tail 12
```
