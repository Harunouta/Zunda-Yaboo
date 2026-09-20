# Speeches (Wikipedia excerpts)

市井が「報道・通達・詔書・会見として聞いた／読み上げられた」言葉の種火データです。スコアリング用の一次史料忠実度ではありません。

## Critical rule: what `publicSpeech` is

**`publicSpeech` は、実際に公衆へ読み上げ・放送・記者会見などで発せられた言葉の要約／抜粋であること。**

含めてよい例:

- 詔書・宣戦の詔の読み下し
- 政府告諭・大号令の布告文
- 首相記者会見・閣議後会見の発言引用
- ラジオ／テレビ声明の発言引用

**禁止（`publicSpeech` に入れない）:**

- 百科事典の事件名定義（例: 「真珠湾攻撃は……の事件である」）
- 「この出来事は〜である」型の名称解説

そうした叙述が必要な場合は `notes` のみに置く。一次の発言原文が Wikipedia に無い場合は、エントリを追加せずスキップするか、既存キーを残して `notes: needs_spoken_source` とする（創作しない）。

優先順位:

1. 一次の発言／読み上げ文（詔書、放送、会見引用）
2. その発言内容の短い言い換え（布告・一人称口調を維持）。`evidence: wikipedia_spoken_paraphrase` とし `notes` に明記
3. 百科叙述しか無い → スキップ（発明しない）

## Files

| File | Role |
|------|------|
| `wikipedia_excerpts.yaml` | **帰属の正本。** |
| `catalog.yaml` | **シミュ向けカタログ。** ローダは `catalog*.yaml` を全部読む（現状は本ファイルのみ） |
| `NEEDS_SPOKEN_SOURCE.yaml` | **一次発言待ちキュー。** 百科リードしか無い月。sim は読まない |

## Rules

- `publicSpeech` は **読み上げ・放送・会見で発せられた言葉**（またはその短い言い換え）。事件名の百科定義は禁止（上記 Critical rule）。
- **要約の長さは人間が後で決める。** catalog 側だけ切ってよい。excerpts 側は帰属正本。
- ライセンスは各エントリに明記。WP は CC-BY-SA、官邸系会見は `government_speech_archive` など。
- catalog と excerpts の `publicSpeech` は同期させる。

## Keys

キーは安定した `snake_case`（例: `pearl_harbor_1941_12`）。`eventIds` は `data/events/japan|world` の既存 ID に紐づける。
