# モデル重みの用意（配布しません）

Zunda-Yaboo は **学習しません**。ホストの [LM Studio](https://lmstudio.ai/) に HTTP で JSON を取りに行くだけです。  
**GGUF / safetensors などの重みは Git に入れません**（[REDISTRIBUTION.md](../REDISTRIBUTION.md)、`models/` は `.gitignore`）。

「重みの作り方」= 自前で学習することではありません。下の手順で **公開モデルをダウンロードして Load** してください。

---

## 1. LM Studio を入れる

1. https://lmstudio.ai/ からアプリをインストール
2. 起動し、**Local Server**（または Developer → Server）で **ポート 1234** を Listen  
   （`Starter/.env` の `GW_LMSTUDIO_PORT` 既定が 1234）

---

## 2. 推奨モデルを Download → Load

LM Studio の **Discover / Search** で次を探し、Download 後に **Load** する。  
表示される **正確な model id** は環境で少し違うことがある → 後で `--probe` で確認。

| 役割 | 検索の目安 | ENV / 用途 |
|------|------------|------------|
| 為政者（ruler） | `qwen3.6-27b` | `RULER_MODEL`、危機時 prose |
| 市井（crowd 等） | `qwen2.5-7b-instruct` | `CROWD_MODEL` |
| フォールバック | `google/gemma-4-e4b` | `CROWD_FALLBACK_MODEL`（同時 Load は避ける） |
| GW 数値 | `qwen3-4b-instruct-2507` | `GW_POLICY_MODEL` |
| GW ID 選択 | `qwen2.5-7b-instruct` | `GW_IDS_MODEL` |
| GW 布告文 | `qwen2.5-14b-instruct` | `GW_PROSE_MODEL` |

詳細表: [MODELS.md](../MODELS.md)、配線図: [docs/MODEL_WIRING.md](../docs/MODEL_WIRING.md)。

### VRAM 注意

- **ruler 27B と、もう一つの巨大モデルを同時 Load しない**（空応答 / terminated の原因）
- まずは ruler + crowd 7B だけ Load して smoke する

---

## 3. コンテナから見えるか確認

スタック起動後:

```powershell
docker exec -w /workspace -e PYTHONPATH=/workspace Zunda-Yaboo python -m src.main --probe
```

出力の model id を `Starter/.env` の `RULER_MODEL` / `CROWD_MODEL` / `GW_*` に合わせ、必要なら:

```powershell
powershell -File .\Starter\up.ps1
```

で gateway / 環境を拾い直す。

---

## 4. 任意: ホストの `models/` フォルダ

小さめ GGUF をファイル置きしたいときだけ、リポジトリ横の `models/`（gitignore）に置く。  
Compose は `${ZUNDA_AI_HOST:-../models}:/models` でマウントする。  
**なくても HTTP（LM Studio）だけで動く。**

---

## 5. dry-run だけ試す場合

LM Studio 無しでもエンジンは回る:

```powershell
docker exec -w /workspace -e PYTHONPATH=/workspace Zunda-Yaboo `
  python -m src.main --no-llm --standard zunda --start 1853-01 --end 1853-03 --run-name starter_dry
```

LLM 台詞・Freedom 切替などは出ない。

---

## やらないこと

- 重みを zip して GitHub に上げる
- このリポジトリ内で fine-tune / 学習して「公式重み」を作る手順の提供
- ずんだもん等の人格コーパスの同梱（`data/restricted/` はローカル任意）
