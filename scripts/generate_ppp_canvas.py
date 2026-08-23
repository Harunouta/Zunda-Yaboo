"""Generate zunda-purchasing-power.canvas.tsx from embed preview JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMBED = ROOT / "logs" / "canvas_ppp_embed_preview.json"
OUT = Path(os.environ.get("CURSOR_CANVAS_DIR", str(ROOT / "logs" / "canvas_out"))) / "zunda-purchasing-power.canvas.tsx"


def main() -> None:
  data = json.loads(EMBED.read_text(encoding="utf-8"))
  OUT.parent.mkdir(parents=True, exist_ok=True)
  src = f"""import {{
  Callout,
  Divider,
  Grid,
  H1,
  H2,
  LineChart,
  Stack,
  Stat,
  Table,
  Text,
}} from "cursor/canvas";

/** Embedded yearly medians from zunda_full_1603_2026 (rice PPP → modern yen). */
const YEARS = {json.dumps(data["years"])};
const FOOD_YEN = {json.dumps(data["foodYen"])};
const DEV_INDEX = {json.dumps(data["dev"])};
const LIVING_PCT = {json.dumps(data["livingPct"])};
const ZUNDA_YEN = {json.dumps(data["zundaYen"])};
const ANKO_YEN = {json.dumps(data["ankoYen"])};
const CATEGORIES = YEARS.map(String);

const FIRST = {json.dumps(data["first"], ensure_ascii=False)};
const LAST = {json.dumps(data["last"], ensure_ascii=False)};
const TENMEI = {json.dumps(data["tenmei"], ensure_ascii=False)};
const MEIJI = {json.dumps(data["meiji"], ensure_ascii=False)};

export default function ZundaPurchasingPower() {{
  const food1603 = "¥" + FIRST.foodYenPerCapita;
  const food2026 = "¥" + LAST.foodYenPerCapita;
  const devLabel = "×" + LAST.developmentIndex;
  const liveLabel = LAST.livingVsModernPct + "%";
  return (
    <Stack gap={{20}} style={{{{ padding: 20 }}}}>
      <Stack gap={{6}}>
        <H1>現代円で見る暮らし（米PPP）</H1>
        <Text tone="secondary">
          Source: logs/runs/zunda_full_1603_2026.jsonl · yearly median · method
          rice_ppp_modern_yen（米1kg≈¥450、現代ひとり食費≈¥40,000/月）
        </Text>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat value={{food1603}} label="1603 食/人・月" tone="danger" />
        <Stat value={{food2026}} label="2026 食/人・月" />
        <Stat value={{devLabel}} label="発展指数 vs 開幕" tone="success" />
        <Stat value={{liveLabel}} label="現代食費に対する比率" />
      </Grid>

      <Callout tone="info">
        開幕は「こんなしょぼい！！」級（現代食費の約0.2%）。天明前後で谷、回復後は開幕比おおよそ3倍。
        ずんだ建値の円換算は早々に天井（≈¥3375）に張り付くので、暮らしの物語は食/人円と発展指数を見る。
      </Callout>

      <Divider />

      <H2>1人あたり食料の現代円換算（食/人・月）</H2>
      <LineChart
        categories={{CATEGORIES}}
        series={{[{{ name: "foodYenPerCapita (yen)", data: FOOD_YEN }}]}}
        height={{260}}
      />
      <Text tone="secondary" size="small">
        X: year (5年刻み) · Y: yen / person / month (rice-kg bridge)
      </Text>

      <H2>発展指数（開幕食料円 = 1.0）</H2>
      <LineChart
        categories={{CATEGORIES}}
        series={{[{{ name: "developmentIndex", data: DEV_INDEX }}]}}
        height={{240}}
      />
      <Text tone="secondary" size="small">
        X: year · Y: ratio vs first-month food yen · 谷＝飢饉・混乱、山＝余裕
      </Text>

      <H2>現代食費に対する比率（%）</H2>
      <LineChart
        categories={{CATEGORIES}}
        series={{[{{ name: "livingVsModern %", data: LIVING_PCT }}]}}
        height={{220}}
      />

      <Divider />

      <H2>時代のスナップショット</H2>
      <Table
        headers={{["年", "食/人¥", "vs現代%", "発展×", "ずんだ¥", "あんこ¥", "感想"]}}
        rows={{[
          [
            String(FIRST.year),
            String(FIRST.foodYenPerCapita),
            String(FIRST.livingVsModernPct),
            String(FIRST.developmentIndex),
            String(FIRST.zundaYen),
            String(FIRST.ankoYen),
            FIRST.vibe,
          ],
          [
            String(TENMEI.year),
            String(TENMEI.foodYenPerCapita),
            String(TENMEI.livingVsModernPct),
            String(TENMEI.developmentIndex),
            String(TENMEI.zundaYen),
            String(TENMEI.ankoYen),
            TENMEI.vibe,
          ],
          [
            String(MEIJI.year),
            String(MEIJI.foodYenPerCapita),
            String(MEIJI.livingVsModernPct),
            String(MEIJI.developmentIndex),
            String(MEIJI.zundaYen),
            String(MEIJI.ankoYen),
            MEIJI.vibe,
          ],
          [
            String(LAST.year),
            String(LAST.foodYenPerCapita),
            String(LAST.livingVsModernPct),
            String(LAST.developmentIndex),
            String(LAST.zundaYen),
            String(LAST.ankoYen),
            LAST.vibe,
          ],
        ]}}
      />

      <H2>参考: 建値の円換算（ずんだ / あんこ）</H2>
      <LineChart
        categories={{CATEGORIES}}
        series={{[
          {{ name: "zundaYen", data: ZUNDA_YEN }},
          {{ name: "ankoYen", data: ANKO_YEN }},
        ]}}
        height={{220}}
      />
      <Text tone="secondary" size="small">
        ずんだ本位ランではあんこ建値が長期で米に対し安くなる。本位制比較は別ランの PPP CSV を見る。
      </Text>
    </Stack>
  );
}}
"""
  OUT.write_text(src, encoding="utf-8")
  print(f"wrote {OUT}")


if __name__ == "__main__":
  main()
