# 小豆本位制（乾燥小豆・あんこ本位の独立派生）

CLI: `--standard azuki`

あんこ本位（`anko`）は**餡に炊いた**備蓄が札の裏付け。こちらは**乾燥した小豆そのもの**（`azukiStock`）が倉の裏付けで、札は `azukiNotes`。砂糖は餡ほど要らない。乾燥なので腐敗も餡より遅い（約18ヶ月相当）。

- マスコットは **あんこもん**（`anko` と同じ）
- `--historical-policy` は江戸金属専用のまま
- 餡市場（`ankoPrice`）は参考表示用に細く残す。本位の価格は `azukiPrice`

```powershell
python -m src.main --no-llm --standard azuki --start 1603-01 --end 1604-12 --opinion-leaders 0 --log logs/runs/smoke_azuki_1603_1604.jsonl
python scripts/smoke_azuki.py
```
