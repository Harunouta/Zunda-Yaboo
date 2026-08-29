# ずんパラ対決比較 — 2ラン重なりビューア

**ずんパラふぉーす**向けの比較 UI です。2本のラン zip を載せ、**両方に存在する `yearMonth` だけ**を並べて見ます。  
画面: [`compare_duel.html`](../web/viewer/compare_duel.html)

---

## 何が見えるか

| レイヤー | 内容 |
|---------|------|
| **数字** | macro 乖離、主貨／米、乖離ソート |
| **世論** | 異常月の意見リーダー 5 人（[`OPINION_ROCKET.md`](OPINION_ROCKET.md)） |
| **農業** | 同じ `yearMonth` × 地域（3）× 職種（4）（[`AGRI_LOGISTICS.md`](AGRI_LOGISTICS.md)） |

マスコットセリフは含めません（ずんパラ本編は別途）。

---

## 同梱デモ

| ファイル | 内容 |
|----------|------|
| [`data/redistributable/duel_packs/sample_zunda_1603_1604.zip`](../data/redistributable/duel_packs/sample_zunda_1603_1604.zip) | 合成デモ（2年） |
| [`data/redistributable/duel_packs/sample_azuki_1603_1604.zip`](../data/redistributable/duel_packs/sample_azuki_1603_1604.zip) | ペア用デモ |

`http://127.0.0.1:8765/compare_duel.html` に 2 本読み込むと動作確認できます。詳細は [`data/redistributable/duel_packs/README.md`](../data/redistributable/duel_packs/README.md)。

---

## 手元のランから zip を作る

```powershell
python scripts/pack_duel_compare_zip.py `
  --log logs/runs/<zunda-run>/monthly.jsonl `
  --out logs/compare_export/zunda_duel.zip `
  --end 2026-08 `
  --label "zunda"

python scripts/pack_duel_compare_zip.py `
  --log logs/runs/<azuki-run>/monthly.jsonl `
  --out logs/compare_export/azuki_duel.zip `
  --label "azuki"
```

`logs/` 配下の出力は **Git にコミットしない** でください。  
LLM セリフやマスコットを含む実ランは手元のみ。公開用には `--no-llm` の史実ペアなど、[`REDISTRIBUTION.md`](../REDISTRIBUTION.md) に沿った zip だけを `duel_packs/` に置きます。

合成デモの再生成: `python scripts/build_duel_public_samples.py`

---

## 関連ファイル

| 項目 | パス |
|------|------|
| 対決 UI | [`web/viewer/compare_duel.html`](../web/viewer/compare_duel.html) |
| zip ビルダー | [`scripts/pack_duel_compare_zip.py`](../scripts/pack_duel_compare_zip.py) |
| 公開サンプル置き場 | [`data/redistributable/duel_packs/`](../data/redistributable/duel_packs/) |
