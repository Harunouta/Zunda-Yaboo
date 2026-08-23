# 経済・イベント中間変数 + 史実政策カタログ

旧 `disasterOverride` / `cropLossExtra` / `worldEffect` は残す。同時に Excel/YAML のショックは農業・物流の中間変数へ写像し、価格は需給（在庫・輸送・不安）側でも動く。

## 方針（マージ）

1. **直接上書きを全廃しない。** 人口ショックと既存 `worldEffect` は従来どおり。備蓄消失は中間変数 `stockSpoilage` が既にあれば二重適用しない。
2. **天候シリーズは触らない。** 地震・火山・津波は `landPollution` / `infraDamage`（イベントデータ）。
3. **心理の具体行動は LLM。** システムは `socialUnrest` / `fiatTrust` を crowd の hoarding に足し、プロンプトに状況を渡す。
*   飢饉の `disasterOverride` は気候のみ。農地毀損の推定は噴火・地震・津波・水害トークンがあるときだけ。
*   同月の `stockSpoilage` は加算せず最大値。旧 `cropLossExtra` からは ×0.4（上限 0.22）。
*   物流は在庫÷地域シェアの密度差が輸送コストを超えたときだけ米を動かす。

## エリア

建国ノードと同じ 3 つ: `tohoku_rim` / `edo_core` / `osaka_hub`。`targetArea`: `ALL` または上記。別名 KANTO→edo、TOHOKU→tohoku、KYUSHU/KANSAI→osaka。

## 減衰

| パターン | 変数 |
|----------|------|
| 単月リセット | stockSpoilage, govDemand, importCostShock, exportDrain |
| 定数回復 0.1/月 | infraDamage, landPollution |
| 割合 ×0.6 | socialUnrest, laborDrain。fiatTrust は 1.0 へ収束 |

## 政策カタログ（係数アイテム）

`data/events/policies/catalog.yaml`

首領は **カタログから選ぶ義務はない。** 毎月 8 枚程度の手札（`policyHand`）が出る。`historicalPolicyIds` は最大 3。空が普通。

選んだ ID は **法令アイテム** として `coeffKit`（harvestBoost / transferBoost / mintBrake / trustRepair / priceDamp / spoilCut）を積み、数ヶ月かけて減衰する。インフレ抑制キットは鋳造を抑え信用を戻し、成長・農・物流キットは作柄と米の移動を厚くする。

農業・物流エージェント（農民・商人・蔵・粉引き、3エリア×4＝12）は CSV ペルソナ＋作付暦＋街道/鉄道。`--llm` 時は毎月 crowd モデルで並列呼び出し。dry-run はルール。ログは `agriLogistics`。

`--historical-policy` もカタログを自動発動しない。数値の史実追従は従来の `historical_track` のみ。飢饉・災害の dry-run では `okumai_relief` を手札扱いする。
