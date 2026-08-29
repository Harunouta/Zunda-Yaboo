# イベントの書き方（Zunda-Yaboo）

歴史の細かさは **データファイルを増やす** だけで足せます。Python を触る必要はほぼありません。

出来事の説明は Wikipedia 等と LLM の推論を混ぜたものです。事実との一致は検証しておらず、一致するようには設計していません（フィクション用）。

## どこを触る？

| やりたいこと | ファイル |
|--------------|----------|
| 日本の出来事を足す・直す（主戦場） | [`japan/timeline.csv`](japan/timeline.csv) + [`japan/catalog.yaml`](japan/catalog.yaml) |
| 世界側の疎いショック | [`world/timeline.csv`](world/timeline.csv) + [`world/catalog.yaml`](world/catalog.yaml) |
| 世界→日本への波及（遅延など） | [`bridges/japan_from_world.csv`](bridges/japan_from_world.csv) |

読み込みコードは [`src/events.py`](../../src/events.py)（ローダのみ）。

## 手順（日本イベントを1つ足す）

### 1. `japan/catalog.yaml` に定義を追加

```yaml
dutch_perry_warning:
  scope: japan_info
  promptForLeader: "長崎経由のオランダ風説：アメリカ艦隊が出航したとの通報。備えは十分か。"
  promptForOpinionLeader: "異国の黒い船が来る、と長崎から噂が先に来た。"
```

必須キー:
- `promptForLeader` … 首領（Qwen）向け。短く具体的に
- `promptForOpinionLeader` … 庶民／オピニオン向け。断片情報でよい

任意キー（中間変数・エリア。詳細は [`MEDIATORS_SPEC.md`](MEDIATORS_SPEC.md)）:
- `targetArea`: `ALL` / `edo_core` / `osaka_hub` / `tohoku_rim`
- `landPollution`, `infraDamage`, `laborDrain`, `stockSpoilage`, `socialUnrest`, `govDemand`, `importCostShock`, `exportDrain`, `fiatTrustShock`

未指定なら従来の `disasterOverride` / `cropLossExtra` / `populationShock` / `epidemicSeverity` / `worldEffect` から推定する。

## 史実政策（選択発動）

[`policies/catalog.yaml`](policies/catalog.yaml) は参考用の史実政策。首領は自由に法令を出してよい。JSON の `historicalPolicyIds` は任意（空でよい）。史実月より早く／遅く使ってもよい。

- `scope`: `japan` | `japan_info` | `world`（既定はファイル置き場に合わせる）
- `disasterOverride`: 0.2〜1.0（小さいほど凶作。未指定なら気候のみ）
- `populationShock`: その月の人口減少率（例 `0.008` = 0.8%）
- `cropLossExtra`: 収量・備蓄への追加ダメージ係数
- `epidemicSeverity`: 疫病の強さ（0〜1、人口ショックに半加算）
- `worldEffect`: 下表の既存 ID のみ（新 ID はコード追記が必要）
- `notes`: メモ（シミュには未使用）

実装済み `worldEffect`（`src/monthly_engine.py`）:

| ID | コード上の効果 |
|----|----------------|
| `sugar_spike` | `sugarStock -= 20`（下限 0） |
| `gold_outflow` | `goldRyo *= 0.95` |
| `hyperinflation` | `zundaNotes`/`ankoNotes` *= 1.2、`hanSatsuCredit *= 0.8`（下限 0.05）。世界側でも可（例: ドイツ・ハイパーインフレ余波） |
| `han_satsu_crisis` | `hanSatsuCredit *= 0.55`（下限 0.05） |
| `oil_spike` | `sugarStock *= 0.92`、`foodBuffer *= 0.97`（エネルギー／ナフサ代理） |
| `chip_spike` | `sugarStock *= 0.94`、`foodBuffer *= 0.985`、紙幣 *= 1.02（半導体不足代理） |

### 2. `japan/timeline.csv` に発火月を追加

```csv
yearMonth,eventId,scope,notes
1852-07,dutch_perry_warning,japan_info,長崎オランダ風説
1853-07,perry_arrival,japan,浦賀来航
```

- 同じ月に複数行 OK（浅間＋天明など）
- `eventId` は catalog に必ず存在すること
- 月は `YYYY-MM`（ゼロ埋め）

### 3. 確認

```powershell
cd <repo root>
$env:PYTHONPATH = (Get-Location).Path
python scripts/validate_events.py
python -c "from src.events import getEventsForMonth, reloadEventData; reloadEventData(); print(getEventsForMonth('1852-07'))"
```

### 統合Excelからの取り込み

仕様: [`UNIFIED_EVENTS_SPEC.md`](UNIFIED_EVENTS_SPEC.md)。
xlsx シート名の想定: `政治` / `地震` / `火山（整形済）` / `水害` / `その他の農作物への被害`

| シート | 状態 | 取り込み |
|--------|------|----------|
| 水害・その他の農作物への被害（飢饉） | **済** | `python scripts/import_famine_flood_events.py --xlsx path/to.xlsx` |
| 火山・インフラ・疫病（名前に「整形済」） | **済** | `python scripts/import_categorized_sheets.py --xlsx path/to.xlsx` |
| 地震（`地震(整形済)`） | **済** | 同上。公開出典は [`japan/README.md`](japan/README.md) |
| 火事（整形済） | **済** | 同上 |
| 政治・争い | 未取込 | 整形済シートが揃い次第、同じスクリプトで取り込み予定 |

```powershell
# 飢饉・水害の再取込
python scripts/import_famine_flood_events.py
# 整形済シート（火山 / インフラ・技術 / 疫病）。政治・地震はシート名に整形済が付くまでスキップ
python scripts/import_categorized_sheets.py
python scripts/validate_events.py
python scripts/smoke_shaped_events.py
```

空欄のプロンプト／係数は Wikipedia 要約ベースで自動補完する。  
バックアップ: `logs/backup_japan_events_before_famine_flood/`。

## scope の使い分け

| scope | 意味 | 例 |
|-------|------|-----|
| `japan` | 国内で起きた／日本に着地した出来事 | ペリー来航、天明飢饉 |
| `japan_info` | まだ本体は来ていないが情報・噂が届いた | オランダ風説 |
| `world` | 外部市場・世界ショック本体 | 世界砂糖危機（疎でよい） |

**世界史フル年表は書かない。** 「その月、日本ノードの統治／噂／物価に効くか？」で切る。

## 世界 → 日本の橋渡し

`bridges/japan_from_world.csv` は、世界 catalog の `eventId` を **日本が感じる月** に並べるだけの薄い表です。

```csv
yearMonth,eventId,scope,notes
1853-08,atlantic_sugar_crisis,world,来航翌月に砂糖ショックが波及
```

先に `world/catalog.yaml` へ同 ID を定義してください。

## やってはいけないこと

- timeline だけ書いて catalog を忘れる（起動時にエラー）
- 新しい `worldEffect` 名を YAML だけに書く（`src/monthly_engine.py` 未対応）
- `data/raw` や論文 PDF をここへ丸ごと置く（イベントは短い文言と係数だけ）

## 既存の例

- 日本: `dutch_perry_warning`（1852-07）など → `japan/`
- 世界: 疎いショック一式 → [`WORLD_HISTORY.md`](WORLD_HISTORY.md) / `world/` + `bridges/`

月が史実とズレていれば `timeline.csv` / `bridges/*.csv` の日付だけ直してください。
