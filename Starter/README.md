# Starter — 第三者・AI 向け起動キット

このフォルダが **Cursor 無しでも** Zunda-Yaboo を起動・検証するための正本です。  
ルートの `HANDOFF.md` や `.cursor/` は不要です。

再現したい状態:

| 要素 | 期待 |
|------|------|
| コンテナ `Zunda-Yaboo` | リポジトリ全体を `/workspace` にマウントした常駐シェル |
| コンテナ `zunda-llm-gw` | `http://127.0.0.1:4000` → ホスト LM Studio `:1234` |
| Viewer | `http://127.0.0.1:8765/` |
| Compare | `http://127.0.0.1:8765/compare.html` |

**モデル重み（GGUF 等）は同梱しません。** 取得手順は [MODELS_SETUP.md](MODELS_SETUP.md)。

---

## 前提

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/)（または Docker Engine + Compose v2）
2. ホストに [LM Studio](https://lmstudio.ai/)（LLM ラン用。dry-run だけなら後回し可）
3. このリポジトリを clone 済み

```text
git clone https://github.com/Harunouta/Zunda-Yaboo.git
cd Zunda-Yaboo
```

---

## チェックリスト（人 / AI 共通）

1. （任意）`Starter/.env.example` を `Starter/.env` にコピーして編集
2. [MODELS_SETUP.md](MODELS_SETUP.md) で推奨モデルを Download → Load（LLM を使う場合）
3. 起動:

```powershell
powershell -File .\Starter\up.ps1
powershell -File .\Starter\start-viewer.ps1
```

```bash
chmod +x Starter/*.sh
./Starter/up.sh
./Starter/start-viewer.sh
```

4. ブラウザで `/` と `/compare.html` を開く
5. 検証:

```powershell
powershell -File .\Starter\verify.ps1
```

詳細は [VERIFY.md](VERIFY.md)。

---

## AI エージェント向け

- **第一入口はこの `Starter/`。** 実装・起動・検証はここを優先する。
- コンテナ名は本番と同じ `Zunda-Yaboo` / `zunda-llm-gw`。既に同名が動いている場合、`up` は recreate する。**走っている長ラン（viewer `/api/job` が `running: true`）があるときは止めない。**
- 重み・`data/restricted/`・`logs/`・`checkpoints/` を commit / push しない（[REDISTRIBUTION.md](../REDISTRIBUTION.md)）。
- dry-run: `docker exec -w /workspace -e PYTHONPATH=/workspace Zunda-Yaboo python -m src.main --no-llm ...`
- LLM: ホスト LM Studio を起動し、gateway `:4000` 経由。viewer の「AI / モデル」でも保存可。

---

## 名前衝突

- **`Zunda-Yaboo` が既に動いているとき**: `up` はそれを**止めない**。ゲートウェイ `zunda-llm-gw` だけ作り直す。
- **`zunda-llm-gw` だけ差し替えたいとき**: そのまま `up` でよい（既存 Zunda-Yaboo 保護）。
- まっさらなマシンでは `up` が両方を起動する。

別名にしたい場合は `Starter/docker-compose.yml` の `container_name` を編集し、スクリプト側の名前も合わせる。

---

## 関連

| 文書 | 内容 |
|------|------|
| [MODELS_SETUP.md](MODELS_SETUP.md) | 重みの入手（配布なし） |
| [VERIFY.md](VERIFY.md) | 検証コマンド |
| [../MODELS.md](../MODELS.md) | 役割と ENV |
| [../VIEWING.md](../VIEWING.md) | 画面の使い方 |
| [../REDISTRIBUTION.md](../REDISTRIBUTION.md) | 公開してよいもの |
