"""Write host canvases from logs/canvas_embed_historical_1603_2026.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMBED = ROOT / "logs" / "canvas_embed_historical_1603_2026.json"
CANVAS_DIR = Path(r"C:\Users\eimia\.cursor\projects\d-Zunda-Yaboo\canvases")


def js(value: object) -> str:
  return json.dumps(value, ensure_ascii=False)


def pick(mapping: dict, *keys: str):
  for key in keys:
    if mapping.get(key) not in (None, []):
      return mapping[key]
  for key in keys:
    if key in mapping:
      return mapping[key]
  return []


def main() -> int:
  data = json.loads(EMBED.read_text(encoding="utf-8"))
  series = data["series"]
  snapshots = pick(data, "snapshots", "snapshots")
  topEvents = pick(data, "topEvents", "topEvents")
  anomalies = list(pick(data, "anomalies", "anomalies"))[:8]
  years = [str(year) for year in series["years"]]
  foodYen = pick(series, "foodYen", "foodYen")
  livingPct = pick(series, "livingPct", "livingPct")
  fidelity = pick(series, "fidelity")
  ricePrice = pick(series, "ricePrice", "ricePrice")
  zundaPrice = pick(series, "zundaPrice")
  ankoPrice = pick(series, "ankoPrice")
  population = pick(series, "population")
  firstSnap = snapshots[0] if snapshots else {}
  lastSnap = snapshots[-1] if snapshots else {}

  def snapField(item: dict, *keys: str) -> str:
    for key in keys:
      if item.get(key) is not None:
        return str(item.get(key))
    return ""

  snapRows = [
    [
      snapField(item, "year"),
      snapField(item, "foodYen", "foodYen"),
      snapField(item, "livingPct", "livingPct"),
      snapField(item, "devIndex", "devIndex"),
      snapField(item, "fidelity"),
      snapField(item, "ricePrice", "ricePrice"),
    ]
    for item in snapshots
  ]
  eventRows = [
    [
      str(item.get("id") or item.get("id") or ""),
      str(item.get("months") or item.get("months") or ""),
    ]
    for item in topEvents
  ]
  anomalyRows = []
  for item in anomalies:
    reasons = item.get("reasons") or item.get("reasons")
    if isinstance(reasons, list):
      reasonText = ", ".join(str(part) for part in reasons)
    else:
      reasonText = str(reasons or item.get("reason") or "")
    anomalyRows.append(
      [
        str(item.get("yearMonth") or item.get("yearMonth") or ""),
        reasonText,
        str(item.get("crowdMood") or item.get("crowdMood") or "")[:80],
      ]
    )

  monthCount = data.get("monthCount") or data.get("monthCount")
  source = data.get("source")
  downsample = data.get("downsample")
  method = data.get("method")
  food1603 = snapField(firstSnap, "foodYen", "foodYen")
  food2026 = snapField(lastSnap, "foodYen", "foodYen")
  fid2026 = snapField(lastSnap, "fidelity")
  live2026 = snapField(lastSnap, "livingPct", "livingPct")

  dashboard = f"""import {{
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

const YEARS = {js(years)};
const FOOD_YEN = {js(foodYen)};
const LIVING_PCT = {js(livingPct)};
const FIDELITY = {js(fidelity)};
const RICE = {js(ricePrice)};
const ZUNDA = {js(zundaPrice)};
const ANKO = {js(ankoPrice)};
const POP = {js(population)};
const SNAP_ROWS = {js(snapRows)};
const EVENT_ROWS = {js(eventRows)};
const ANOMALY_ROWS = {js(anomalyRows)};

export default function ZundaRunDashboard() {{
  return (
    <Stack gap={{20}} style={{{{ padding: 20 }}}}>
      <Stack gap={{6}}>
        <H1>historical 1603-2026 年次ダッシュボード</H1>
        <Text tone="secondary">
          Source: {source} · {monthCount} months · {downsample} · PPP {method}
        </Text>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat value="{food1603}" label="1603 食/人円 (median)" />
        <Stat value="{food2026}" label="2026 食/人円 (median)" tone="success" />
        <Stat value="{fid2026}" label="2026 fidelity" />
        <Stat value="{monthCount}" label="months in JSONL" />
      </Grid>

      <Callout tone="info">
        JSONL は fidelity/PPP 修正前ラン。PPP 系列は era_basket_times_grain_stock
        で閲覧側再計算。シミュ係数は未変更。
      </Callout>

      <H2>食/人円（年次中央値）</H2>
      <LineChart
        categories={{YEARS}}
        series={{[{{ name: "foodYenPerCapita (yen / person / month)", data: FOOD_YEN }}]}}
        height={{260}}
      />
      <Text tone="secondary" size="small">
        X: year · Y: yen / person / month
      </Text>

      <H2>現代食費に対する比率（%）</H2>
      <LineChart
        categories={{YEARS}}
        series={{[{{ name: "livingVsModern (%)", data: LIVING_PCT }}]}}
        height={{220}}
      />
      <Text tone="secondary" size="small">X: year · Y: percent of modern food budget</Text>

      <Divider />

      <H2>historicalFidelity.score</H2>
      <LineChart
        categories={{YEARS}}
        series={{[{{ name: "fidelity score (0-1)", data: FIDELITY }}]}}
        height={{220}}
      />
      <Text tone="secondary" size="small">X: year · Y: score · yearly median</Text>

      <H2>米・ずんだ・あんこ価格（sim units）</H2>
      <LineChart
        categories={{YEARS}}
        series={{[
          {{ name: "ricePrice", data: RICE }},
          {{ name: "zundaPrice", data: ZUNDA }},
          {{ name: "ankoPrice", data: ANKO }},
        ]}}
        height={{260}}
      />
      <Text tone="secondary" size="small">X: year · Y: sim price</Text>

      <H2>人口（年次中央値）</H2>
      <LineChart
        categories={{YEARS}}
        series={{[{{ name: "population", data: POP }}]}}
        height={{200}}
      />
      <Text tone="secondary" size="small">X: year · Y: simulated population</Text>

      <H2>時代スナップショット</H2>
      <Table
        headers={{["year", "food yen", "vs now %", "dev x", "fidelity", "rice"]}}
        rows={{SNAP_ROWS}}
      />

      <H2>出現月が多いイベント</H2>
      <Table headers={{["event id", "months"]}} rows={{EVENT_ROWS}} />

      <H2>異常月（先頭）</H2>
      <Table headers={{["yearMonth", "reasons", "mood"]}} rows={{ANOMALY_ROWS}} />
    </Stack>
  );
}}
"""

  ppp = f"""import {{
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

const YEARS = {js(years)};
const FOOD_YEN = {js(foodYen)};
const LIVING_PCT = {js(livingPct)};
const SNAP_ROWS = {js(snapRows)};

export default function ZundaPurchasingPower() {{
  return (
    <Stack gap={{20}} style={{{{ padding: 20 }}}}>
      <Stack gap={{6}}>
        <H1>現代円で見る暮らし（時代バスケット×在庫）</H1>
        <Text tone="secondary">
          Source: {source} · yearly median · method {method} ·
          食/人円はバッファkgではない
        </Text>
      </Stack>

      <Grid columns={{3}} gap={{12}}>
        <Stat value="{food1603}" label="1603 食/人・月" />
        <Stat value="{food2026}" label="2026 食/人・月" tone="success" />
        <Stat value="{live2026}%" label="2026 vs 現代食費" />
      </Grid>

      <Callout tone="info">
        旧 Canvas は米PPPの説明のままだった。いまは era_basket_times_grain_stock。
        この historical ログは修正前ランなので、値は閲覧側再計算。
      </Callout>

      <H2>1人あたり食料の現代円換算</H2>
      <LineChart
        categories={{YEARS}}
        series={{[{{ name: "foodYenPerCapita (yen)", data: FOOD_YEN }}]}}
        height={{260}}
      />
      <Text tone="secondary" size="small">X: year · Y: yen / person / month</Text>

      <H2>現代食費に対する比率（%）</H2>
      <LineChart
        categories={{YEARS}}
        series={{[{{ name: "livingVsModern %", data: LIVING_PCT }}]}}
        height={{220}}
      />

      <Divider />

      <H2>節目</H2>
      <Table
        headers={{["year", "food yen", "vs now %", "dev x", "fidelity", "rice"]}}
        rows={{SNAP_ROWS}}
      />
    </Stack>
  );
}}
"""

  CANVAS_DIR.mkdir(parents=True, exist_ok=True)
  dashPath = CANVAS_DIR / "zunda-run-dashboard.canvas.tsx"
  pppPath = CANVAS_DIR / "zunda-purchasing-power.canvas.tsx"
  dashPath.write_text(dashboard, encoding="utf-8")
  pppPath.write_text(ppp, encoding="utf-8")
  print(f"wrote {dashPath}")
  print(f"wrote {pppPath}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
