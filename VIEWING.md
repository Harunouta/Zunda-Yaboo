# 見て遊ぶ

見方はふたつです。**ブラウザ**は月次の画面と短い起動、**CUI**はターミナルでセリフを流す／メニューから操作します。公開向けの大きな GUI はありません。

作業場所はクローンしたリポジトリ直下（Docker なら `/workspace`）です。ホストのドライブ文字は使いません。

```powershell
cd <このリポジトリ>
$env:PYTHONPATH = (Get-Location).Path
$env:PYTHONIOENCODING = "utf-8"
```

---

## ブラウザで見る

Windows から `http://127.0.0.1:8765/` を開きます。コンテナ内の `127.0.0.1` はホストから見えないので、**サーバは `0.0.0.0:8765`、ホスト公開は `127.0.0.1:8765` だけ**です。

1. Docker コンテナ名 `Zunda-Yaboo` が動いていること。
2. **初回だけ**（8765 がまだ公開されていないとき）リポジトリ直下で:

```powershell
powershell -File .\scripts\republish_viewer_port.ps1
```

モデル置き場をマウントし直す場合は、ホスト側パスを `ZUNDA_AI_HOST` に入れてから同じスクリプトを実行します（未設定ならリポジトリの `models` フォルダ）。

3. `open_viewer.bat` をダブルクリックする。Docker 内で viewer が立ち上がり、Windows のブラウザが開きます。

画面でできること:

- ランフォルダ `logs/runs/<名前>/monthly.jsonl` を選ぶ
- 「AI / モデル」で LM Studio または OpenAI と役モデルを保存（Cursor 不要）
- 実行中は推論中の年月（この表示は **今動いている閲覧サーバのメモリ**。サーバを再起動すると sim が生きていても消える。HTML だけの変更では再起動しない）
- 「その年を見る」で布告・マスコット・世論
- ポップアップが消えても `logs/runs/<名前>/monthly.jsonl` の末尾と `logs/viewer_job.out` で進捗は読める

同じ起動: `python scripts/operator_cui.py` の `v`、または `python scripts/operator_cui.py --serve-viewer`

---

## CUI（ターミナル）で見る

セリフが月ごとに流れるのはこちらです。ログが無い preset は失敗するので、先に `--list-presets` でパスを確認してください。

操作メニュー:

```powershell
python scripts/operator_cui.py
python scripts/operator_cui.py --list-presets
```

再生の例:

```powershell
python scripts/play_run.py --preset full-zunda --only-events --delay 0.35
python scripts/play_run.py --preset covid-modern --delay 0.4
python scripts/play_run.py --preset tenmei --only-events --delay 0.35
python scripts/play_run.py --preset historical-full --only-events --delay 0.2
```

preset 名: `full-zunda` / `tenmei` / `covid-modern` / `perry` / `world-modern` / `floods-1950s` / `azuki-tenmei` / `azuki-1853` / `historical-full`

短い新規ランをその場で回して再生: `python scripts/play_run.py --live --start 1853-01 --end 1853-12`

---

## Cursor Canvas（任意）

チャット横の年次グラフ用。埋め込み JSON:

```powershell
python scripts/export_canvas_embed.py --log logs/runs/historical_1603_2026.jsonl
```

---

## セリフ一覧・価格・PPP

```powershell
python scripts/export_speech_log.py --log logs/runs/overnight_b_llm_1853.jsonl
python scripts/export_price_csv.py --log logs/runs/zunda_full_1603_2026.jsonl --out logs/runs/zunda_full_1603_2026_prices.csv
python scripts/analyze_run.py --log logs/runs/world_era_1801_2026.jsonl
python scripts/export_purchasing_power.py --log logs/runs/zunda_full_1603_2026.jsonl
python scripts/preview_month_log.py --log logs/runs/overnight_b_llm_1853.jsonl --tail 12
```

- `*.speech.md` 読み物 / `*.speech.jsonl` 機械用
- 現代円の見方は [`PURCHASING_POWER.md`](PURCHASING_POWER.md)
