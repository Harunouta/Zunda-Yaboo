# Zunda-Yaboo — 江戸幕府〜現代 月次経済シミュレーション

**ver1** — このバージョンは「ずんパラふぉーすネタ用」です。

江戸幕府開府（**1603-01**）から **2026-08** まで、1ヶ月=1ターンで回します。  
GUIなし。通貨制度は CLI の `--standard`（ラジオ相当）で選択します。

## 注意（必読）

- **非公式です。** 東北ずん子・ずんだもんプロジェクト、その他いかなる公式とは無関係です。
- **フィクション用のシミュレーションプログラムです。** 学術論文・報道・防災・投資・歴史教育の一次資料ではありません。
- 飢饉・洪水・疫病・戦争などの出来事の説明は、Wikipedia 等の二次情報と LLM の推論を混ぜたものです。**事実と一致するかは検証していません。** 史実と一致するように設計してもいません。
- ずんだもん／あんこもんの詳細コーパス（聖書）はこのリポジトリでは**非公開**です。無くても短いフォールバックで動きます。

見て遊ぶ:

- **ブラウザ** … `open_viewer.bat` → `http://127.0.0.1:8765/`（月次画面・短い起動）。比較用のセリフ無し zip は [`data/redistributable/compare_packs/`](data/redistributable/compare_packs/) を `/compare.html` に載せる。
- **CUI** … ターミナルで `python scripts/operator_cui.py` または `python scripts/play_run.py --preset …`

手順の本体は [`VIEWING.md`](VIEWING.md)。

- 日本史イベント（飢饉〜火事・争い・政策・法令カタログ）→ [`data/events/README.md`](data/events/README.md)
- Excel 仕様 → [`data/events/UNIFIED_EVENTS_SPEC.md`](data/events/UNIFIED_EVENTS_SPEC.md)

## 妥当性の基準

1. **`edo_metal` + `--historical-policy`**: 史実寄り政策で回したとき、各月の `historicalFidelity.score` が歴史アンカーに追従すること
2. **開府後およそ10年（1603-01〜1612-12）**: `zunda` / `anko` が人口崩壊せず動き、マスコット発話が出ること

```powershell
python -m src.main --validate-baseline
# または
python scripts/validate_baseline.py
```

## ずんだ／あんこ価格の watching

どの本位制でも（`edo_metal` 含む）、開府時点から両市場が存在するという設定です。  
毎月のログに `prices` が入る:

- `zundaPrice` / `ankoPrice` / `azukiPrice`
- `ricePrice` / `goldPrice` / `silverPrice`
- `zundaVsRice` / `ankoVsRice` / `azukiVsRice` / `zundaVsAnko`

```powershell
python -m src.main --no-llm --standard edo_metal --historical-policy --start 1603-01 --end 1612-12
```

## 通貨パターン

| `--standard` | 内容 |
|--------------|------|
| `zunda` | 江戸幕府・ずんだ本位 |
| `anko` | 江戸幕府・あんこ本位（餡） |
| `azuki` | 江戸幕府・小豆本位（乾燥小豆。あんこ本位の独立派生） |
| `edo_metal` | 米（石）＋金（両）＋銀（匁）＋藩札 |
| `dollar` | ドル本位（実装のみ。現代FX折れ線。価値合わせは後） |
| `historical` | 江戸金属→1897金本位→1949ドル（`data/economy/monetary_regimes.csv`） |

詳細: [`DOLLAR_STANDARD.md`](DOLLAR_STANDARD.md) / [`AZUKI_STANDARD.md`](AZUKI_STANDARD.md)

## 庶民マスコット（1人だけ）

| `--standard` | マスコット |
|--------------|-----------|
| `zunda` | ずんだもん（語尾「のだ」） |
| `anko` | あんこもん（語尾「もん」） |
| `azuki` | あんこもん（語尾「もん」） |
| `edo_metal` | なし |
| `dollar` | なし |

詳細コーパス（ずんだもん／あんこもんの聖書）は **非公開**です。このリポジトリにも、公開ダウンロード先にも置きません。手元にある場合のみ `data/restricted/` へ（[手順](data/restricted/README.md)）。無い場合は短いフォールバックで動作します。  
キャラクターの利用は [ずん子ガイドライン](https://zunko.jp/guideline.html) に従う想定です。

毎月のログ `crowd.mascotId` / `crowd.mascotSpeech` に口調つき発話が入ります。

歴史イベントは **`data/events/`**（CSV/YAML）。編集手順は [data/events/README.md](data/events/README.md)。検証: `python scripts/validate_events.py`。

LM Studio 既定: 統治 `qwen3.6-27b`、crowd `qwen2.5-7b-instruct`（詳細 [MODELS.md](MODELS.md)）。  
27B と別の大モデルを同時 Load すると `terminated` になりやすいので、crowd は 7B を推奨。

月次のどこが数式でどこが LLM かは [docs/RULES_VS_LLM.md](docs/RULES_VS_LLM.md)。農の三角・政策カード・オピニオン伝播などの図は [docs/INTERNALS.md](docs/INTERNALS.md)。

## GitHub

リモート: [Harunouta/Zunda-Yaboo](https://github.com/Harunouta/Zunda-Yaboo)（いまは private。公開するときは GitHub の Visibility を public に切り替えるだけでよい）。

再配布の切り分けは **[REDISTRIBUTION.md](REDISTRIBUTION.md)** と **[licenses/THIRD_PARTY.md](licenses/THIRD_PARTY.md)**。

| 区分 | 置き場 |
|------|--------|
| 同梱する | `src/`、`scripts/`、`config/`、`data/events/`、`data/redistributable/`（セリフ無し compare zip 含む）、Dockerfile 等 |
| 同梱しない | `data/restricted/` のコーパス（非公開）、`logs/`、`checkpoints/`、モデル重み、Cursor/エージェント用指示（`HANDOFF.md`、`.cursor/` など） |

コードは MIT（[LICENSE](LICENSE)）。ずんだもん／あんこもんは [ずん子ガイドライン](https://zunko.jp/guideline.html) に従う非公式利用で、MIT の対象外です。聖書は公開しません。

Excel からの再取込はユーザーの手元の xlsx を `--xlsx` で渡す（ホームの `Downloads` も見る）。リポジトリにはシート本体を入れません。

## 前提

- 作業ディレクトリ: クローンしたリポジトリ直下（コンテナでは `/workspace`）
- 追加 SLM 置き場: コンテナ `/models`（ホスト側パスは `ZUNDA_AI_HOST` または `ZUNDA_AI_DIR` で指定。既定のドライブ文字は持たない）
- LLM: ホストの LM Studio（統治 Qwen3.6-27B ＋ crowd Qwen2.5-7B）
- 遅い実行OK。チェックポイント `checkpoints/latest.json` で再開可能

## コンテナ（開発用 Zunda-Yaboo）

コンテナ名 `Zunda-Yaboo` を使う想定です。

- マウント例: リポジトリ → `/workspace`、モデルディレクトリ → `/models`
- `host.docker.internal` → LM Studio

```powershell
docker exec -it Zunda-Yaboo bash
cd /workspace
pip install -r requirements.txt
python -m src.main --probe
python -m src.main --standard zunda --start 1853-01 --end 1853-12 --llm
```

## 別マシン向け docker run

```bash
docker build -t zunda-yaboo:latest .

docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e LM_STUDIO_HOST=host.docker.internal \
  -e LM_STUDIO_PORT=1234 \
  -e RULER_MODEL=qwen3.6-27b \
  -e CROWD_MODEL=qwen2.5-7b-instruct \
  -v ${PWD}/logs:/workspace/logs \
  -v ${PWD}/checkpoints:/workspace/checkpoints \
  -v /path/to/Zunda-AI:/models \
  zunda-yaboo:latest \
  --standard zunda --start 1603-01 --end 2026-08
```

長走の途中再開:

```bash
docker run --rm ... zunda-yaboo:latest --resume --standard zunda --end 2026-08
```

## フル期間の目安

- 月数: 1603-01 〜 2026-08 ≈ **5084 ヶ月**
- LLMあり: 1月あたり数秒〜数十秒 → **数時間〜数日**かかり得ます
- まずはスモーク:

```powershell
python -m src.main --standard zunda --start 1853-01 --end 1853-12 --llm
```

その後フル（1603〜2026-08）:

```powershell
python -m src.main --standard zunda --start 1603-01 --end 2026-08 --llm
python -m src.main --standard edo_metal --historical-policy --start 1603-01 --end 2026-08 --no-llm
```

史実追従モード（妥当性用）:

```powershell
python -m src.main --standard edo_metal --historical-policy --no-llm --start 1603-01 --end 1868-12
```

## 出力

- `logs/monthly_run.jsonl` — 毎月の法令・政策・庶民感情・マクロ
- `logs/anomaly_months.json` — 異常月（動画ネタ用）
- `checkpoints/latest.json` — 再開用

## Dry-run（LLMなし）

```powershell
python -m src.main --no-llm --standard edo_metal --start 1603-01 --end 2026-08
```
