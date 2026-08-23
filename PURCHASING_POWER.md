# 現代円・購買力（閲覧用）

シミュレーションのずんだ / あんこ / 米を、**いまの円の感覚**に橋渡しする閲覧用指標です。学術CPIではありません。

## 換算の考え方

1. **商品の円**（ずんだ・あんこ・小豆）: 従来どおり米 PPP。`sim ricePrice = 1.0` ≈ 米 1kg、現代小売米 ≈ **¥450/kg**
2. **食/人円**: バッファを kg と見なさない。  
   - 時代バスケット（1603 は月 ¥520 前後、2026 は月 ¥39,000 前後）  
   - × 在庫月数 / 目安6ヶ月（凶作で在庫が減ると下がる）
3. **vs現代%** = 食/人円 ÷ 現代ひとり食費目安 **¥40,000/月**
4. **発展指数** = 食/人円 ÷ ラン開始月の食/人円
5. 両（edo_metal）: 参考で `1両 ≈ 1石 ≈ 150kg × ¥450`

感想ラベル（`vibe`）例: `こんなしょぼい！！` / `発展してきた` / `こんなに経済発展した！` / `現代に近い食のゆとり`

`method` は `era_basket_times_grain_stock`。

## 使い方

```powershell
cd D:\Zunda-Yaboo
$env:PYTHONPATH = "D:\Zunda-Yaboo"

python scripts/export_purchasing_power.py --log logs/runs/zunda_full_1603_2026.jsonl
python scripts/analyze_run.py --log logs/runs/zunda_full_1603_2026.jsonl
python scripts/play_run.py --preset tenmei --delay 0.3
```

新規ランでは月次 JSONL に `purchasingPower` ブロックが入ります。古い JSONL は `export_purchasing_power` か再生時に再計算できます。

実装: `src/purchasing_power.py`
