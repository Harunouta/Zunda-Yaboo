# 検証手順

`Starter/up` と `start-viewer` のあと、またはいつでも。

## 自動

```powershell
powershell -File .\Starter\verify.ps1
```

```bash
./Starter/verify.sh
```

確認内容:

1. `zunda-llm-gw` / `Zunda-Yaboo` が Running
2. `http://127.0.0.1:4000/health`
3. `http://127.0.0.1:8765/` と `/compare.html` が 200
4. コンテナ内 dry-run（`1853-01`..`1853-03`、`--no-llm`）

## 手作業

```powershell
docker ps --filter name=zunda-llm-gw --filter name=Zunda-Yaboo
Invoke-WebRequest http://127.0.0.1:4000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8765/ -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8765/compare.html -UseBasicParsing
Invoke-RestMethod http://127.0.0.1:8765/api/job
```

```bash
curl -fsS http://127.0.0.1:4000/health
curl -fsSI http://127.0.0.1:8765/
curl -fsSI http://127.0.0.1:8765/compare.html
```

## LLM があるとき（任意）

LM Studio でモデル Load 済みなら:

```powershell
docker exec -w /workspace -e PYTHONPATH=/workspace Zunda-Yaboo python -m src.main --probe
docker exec -w /workspace -e PYTHONPATH=/workspace Zunda-Yaboo `
  python -m src.main --llm --standard zunda --start 1853-01 --end 1853-03 --run-name starter_llm_smoke
```

失敗しやすい点: gateway 未起動、LM Studio が 1234 で Listen していない、モデル id 不一致、VRAM 不足。

## 失敗時

| 症状 | 確認 |
|------|------|
| 8765 接続拒否 | `start-viewer` 済みか。`docker port Zunda-Yaboo 8765` |
| 4000 失敗 | `docker logs zunda-llm-gw`、LM Studio :1234 |
| dry-run 失敗 | `PYTHONPATH=/workspace`、リポジトリが `/workspace` にマウントされているか |
| compare 404 | `web/viewer/compare.html` が clone に含まれているか |
