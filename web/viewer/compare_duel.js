/* Duel compare: overlap-only, opinion 5 + agri regional. Public-redistributable UI. */

const duelZipFiles = document.getElementById("duelZipFiles");
const duelLoadStatus = document.getElementById("duelLoadStatus");
const duelOverlapMeta = document.getElementById("duelOverlapMeta");
const duelPackLegend = document.getElementById("duelPackLegend");
const duelRangeMeta = document.getElementById("duelRangeMeta");
const duelOnlyEvents = document.getElementById("duelOnlyEvents");
const duelOnlyBigChanges = document.getElementById("duelOnlyBigChanges");
const duelMonthList = document.getElementById("duelMonthList");
const duelDivergenceList = document.getElementById("duelDivergenceList");
const duelDetail = document.getElementById("duelDetail");
const duelDetailTitle = document.getElementById("duelDetailTitle");
const duelMacroGrid = document.getElementById("duelMacroGrid");
const duelOpinionTable = document.getElementById("duelOpinionTable");
const duelAgriGrid = document.getElementById("duelAgriGrid");
const duelChartTooltip = document.getElementById("duelChartTooltip");

const DUEL_RUN_COLORS = ["#8BC34A", "#C45C48"];
const CHART_PAD = { left: 44, right: 12, top: 12, bottom: 28 };
const OPINION_ROSTER = [
  { id: "elder_village", label: "村の長老" },
  { id: "merchant_traveler", label: "噂好きの行商人" },
  { id: "cult_preacher", label: "新興宗教の教祖" },
  { id: "smuggler_broker", label: "闇市の仲買" },
  { id: "frontier_settler", label: "辺境の開拓百姓" },
];
const AREA_ORDER = [
  { id: "tohoku_rim", label: "東北縁" },
  { id: "edo_core", label: "江戸核心" },
  { id: "osaka_hub", label: "大坂・畿内" },
];
const ROLE_ORDER = [
  { id: "farmer", label: "作人" },
  { id: "merchant", label: "商人" },
  { id: "warehouse", label: "蔵" },
  { id: "miller", label: "粉屋" },
];
const INTENT_LABELS = {
  flee: "逃げ",
  hoard: "溜め",
  black_market: "闇市",
  organize: "結社",
  comply: "従順",
};

let duelPacks = [];
let overlapRange = { from: "", to: "" };
let selectedYearMonth = "";

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function primaryPriceSpec(standard) {
  const key = String(standard || "").toLowerCase();
  if (key === "anko") return { field: "ankoPrice", labelJa: "あんこ" };
  if (key === "azuki") return { field: "azukiPrice", labelJa: "小豆" };
  return { field: "zundaPrice", labelJa: "ずんだ" };
}

function formatNum(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 100) return value.toFixed(1);
  return value.toFixed(3);
}

function divergenceScore(left, right) {
  if (!left || !right) return 0;
  let score = 0;
  const popL = left.population;
  const popR = right.population;
  if (typeof popL === "number" && typeof popR === "number") {
    score += Math.abs(popL - popR) / Math.max(Math.abs(popL), Math.abs(popR), 1);
  }
  const foodL = left.purchasingPower && left.purchasingPower.foodYenPerCapita;
  const foodR = right.purchasingPower && right.purchasingPower.foodYenPerCapita;
  if (typeof foodL === "number" && typeof foodR === "number") {
    score += Math.abs(foodL - foodR) / Math.max(Math.abs(foodL), Math.abs(foodR), 1);
  }
  const ratioL = left.primaryVsRice;
  const ratioR = right.primaryVsRice;
  if (typeof ratioL === "number" && typeof ratioR === "number") {
    score += Math.abs(ratioL - ratioR) / Math.max(Math.abs(ratioL), Math.abs(ratioR), 0.001);
  }
  return score;
}

function drawSimpleChart(canvas, labels, seriesList) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const plotW = width - CHART_PAD.left - CHART_PAD.right;
  const plotH = height - CHART_PAD.top - CHART_PAD.bottom;
  let minVal = Infinity;
  let maxVal = -Infinity;
  for (const series of seriesList) {
    for (const value of series.data) {
      if (typeof value !== "number") continue;
      minVal = Math.min(minVal, value);
      maxVal = Math.max(maxVal, value);
    }
  }
  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || labels.length < 2) {
    ctx.fillStyle = "#9d9d9d";
    ctx.fillText("no overlap series", 8, 20);
    return;
  }
  if (minVal === maxVal) maxVal = minVal + 1;
  const plotX = (index) =>
    CHART_PAD.left + (index / Math.max(labels.length - 1, 1)) * plotW;
  const plotY = (value) =>
    CHART_PAD.top + plotH - ((value - minVal) / (maxVal - minVal)) * plotH;
  ctx.strokeStyle = "#3c3c3c";
  ctx.beginPath();
  ctx.moveTo(CHART_PAD.left, CHART_PAD.top);
  ctx.lineTo(CHART_PAD.left, CHART_PAD.top + plotH);
  ctx.lineTo(CHART_PAD.left + plotW, CHART_PAD.top + plotH);
  ctx.stroke();
  seriesList.forEach((series, seriesIndex) => {
    ctx.strokeStyle = series.color || DUEL_RUN_COLORS[seriesIndex];
    ctx.beginPath();
    let drawing = false;
    series.data.forEach((value, index) => {
      if (typeof value !== "number") {
        drawing = false;
        return;
      }
      const x = plotX(index);
      const y = plotY(value);
      if (!drawing) {
        ctx.moveTo(x, y);
        drawing = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.fillStyle = series.color || DUEL_RUN_COLORS[seriesIndex];
    ctx.fillText(series.name, CHART_PAD.left + 8 + seriesIndex * 160, CHART_PAD.top + 10);
  });
  ctx.fillStyle = "#9d9d9d";
  ctx.fillText(String(labels[0]), CHART_PAD.left, height - 6);
  ctx.fillText(String(labels[labels.length - 1]), CHART_PAD.left + plotW - 40, height - 6);
}

function alignYears(years, srcYears, values) {
  const map = new Map();
  (srcYears || []).forEach((year, index) => map.set(Number(year), values[index]));
  return years.map((year) => (map.has(year) ? map.get(year) : null));
}

function intersectYearMonths(lists) {
  if (!lists.length) return [];
  let set = new Set(lists[0]);
  for (let index = 1; index < lists.length; index += 1) {
    const next = new Set();
    for (const ym of set) {
      if (lists[index].includes(ym)) next.add(ym);
    }
    set = next;
  }
  return Array.from(set).sort();
}

async function loadDuelZipFiles(fileList) {
  const files = Array.from(fileList || []);
  if (files.length !== 2) {
    throw new Error("duel zip はちょうど 2 本必要です");
  }
  duelLoadStatus.textContent = "zip を読んでいます…";
  const packs = [];
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    const data = await fetchJson(`/api/compare/load?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: file,
    });
    packs.push({
      stem: data.stem,
      label: data.label || file.name.replace(/\.zip$/i, ""),
      color: DUEL_RUN_COLORS[index],
      standard: data.standard,
      span: data.span,
    });
  }
  duelPacks = packs;
  renderDuelLegend();
  duelLoadStatus.textContent = "2 本載せました";
  await renderDuelCompare();
}

function renderDuelLegend() {
  duelPackLegend.innerHTML = "";
  duelPacks.forEach((pack, index) => {
    const chip = document.createElement("span");
    chip.className = "packChip";
    chip.innerHTML = `<span class="packDot" style="background:${pack.color}"></span><span class="packName">${pack.label}</span>`;
    duelPackLegend.appendChild(chip);
  });
}

async function fetchOverlapMonths() {
  const ymLists = [];
  for (const pack of duelPacks) {
    const payload = await fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/months`);
    ymLists.push((payload.months || []).map((item) => item.yearMonth));
  }
  return intersectYearMonths(ymLists);
}

async function renderDuelCompare() {
  if (duelPacks.length !== 2) return;
  const overlapMonths = await fetchOverlapMonths();
  if (!overlapMonths.length) {
    duelOverlapMeta.textContent = "重なり月がありません";
    return;
  }
  overlapRange = { from: overlapMonths[0], to: overlapMonths[overlapMonths.length - 1] };
  duelOverlapMeta.textContent = `重なり期間のみ表示: ${overlapRange.from} … ${overlapRange.to}（${overlapMonths.length} ヶ月）`;

  const seriesPayloads = await Promise.all(
    duelPacks.map((pack) => fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/series`))
  );
  const overlapYears = overlapMonths.map((ym) => Number(ym.slice(0, 4)));
  const uniqueYears = Array.from(new Set(overlapYears)).sort((a, b) => a - b);
  const yearLabels = uniqueYears.map(String);

  drawSimpleChart(
    document.getElementById("duelChartPop"),
    yearLabels,
    duelPacks.map((pack, index) => ({
      name: pack.label,
      color: pack.color,
      data: alignYears(uniqueYears, seriesPayloads[index].series.years, seriesPayloads[index].series.population || []),
    }))
  );
  drawSimpleChart(
    document.getElementById("duelChartFood"),
    yearLabels,
    duelPacks.map((pack, index) => ({
      name: pack.label,
      color: pack.color,
      data: alignYears(uniqueYears, seriesPayloads[index].series.years, seriesPayloads[index].series.foodYen || []),
    }))
  );
  const priceSeries = [];
  duelPacks.forEach((pack, index) => {
    const spec = primaryPriceSpec(pack.standard || seriesPayloads[index].standard);
    const series = seriesPayloads[index].series || {};
    priceSeries.push({
      name: `${pack.label} 米`,
      color: pack.color,
      data: alignYears(uniqueYears, series.years, series.ricePrice || []),
    });
    priceSeries.push({
      name: `${pack.label} ${spec.labelJa}`,
      color: pack.color,
      data: alignYears(uniqueYears, series.years, series[spec.field] || []),
    });
  });
  drawSimpleChart(document.getElementById("duelChartPrice"), yearLabels, priceSeries);

  duelRangeMeta.textContent = duelPacks
    .map((pack, index) => {
      const payload = seriesPayloads[index];
      return `${pack.label}: ${(payload.range || []).join("..")} · ${payload.monthCount || "?"}ヶ月`;
    })
    .join("  /  ");

  await fillDivergenceList(overlapMonths);
  await fillDuelMonthList(overlapMonths);
}

async function fillDivergenceList(overlapMonths) {
  duelDivergenceList.innerHTML = "";
  const rows = [];
  for (const yearMonth of overlapMonths) {
    const views = await Promise.all(
      duelPacks.map((pack) =>
        fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/month/${encodeURIComponent(yearMonth)}`).catch(() => null)
      )
    );
    if (!views[0] || !views[1]) continue;
    const events = views[0].events || views[1].events || [];
    if (!events.length) continue;
    const score = divergenceScore(views[0], views[1]);
    if (score <= 0) continue;
    rows.push({ yearMonth, score, events, views });
  }
  rows.sort((left, right) => right.score - left.score);
  for (const row of rows.slice(0, 40)) {
    const item = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = `${row.yearMonth} · 乖離 ${row.score.toFixed(3)} · ${row.events.slice(0, 3).join(", ")}`;
    btn.addEventListener("click", () => showDuelMonth(row.yearMonth));
    item.appendChild(btn);
    duelDivergenceList.appendChild(item);
  }
}

async function fillDuelMonthList(overlapMonths) {
  duelMonthList.innerHTML = "";
  const params = new URLSearchParams();
  params.set("from", overlapRange.from);
  params.set("to", overlapRange.to);
  if (duelOnlyEvents.checked) params.set("onlyEvents", "1");
  if (duelOnlyBigChanges.checked) params.set("onlyBigChanges", "1");

  const byYm = new Map();
  for (const pack of duelPacks) {
    const payload = await fetchJson(
      `/api/runs/${encodeURIComponent(pack.stem)}/months?${params.toString()}`
    );
    for (const month of payload.months || []) {
      if (!byYm.has(month.yearMonth)) byYm.set(month.yearMonth, {});
      byYm.get(month.yearMonth)[pack.stem] = month;
    }
  }
  const yearMonths = overlapMonths.filter((ym) => byYm.has(ym));
  for (const yearMonth of yearMonths) {
    const item = document.createElement("li");
    item.dataset.yearMonth = yearMonth;
    const row = document.createElement("button");
    row.type = "button";
    row.className = "monthRow";
    const marks = duelPacks.map((pack) => {
      const month = byYm.get(yearMonth)[pack.stem];
      if (!month) return `${pack.label}: —`;
      const bits = [];
      if (month.eventCount) bits.push(`e${month.eventCount}`);
      if (month.bigChange) bits.push("▲");
      return `${pack.label}: ${bits.join(" ") || "・"}`;
    });
    row.textContent = `${yearMonth}  ${marks.join(" · ")}`;
    row.addEventListener("click", () => showDuelMonth(yearMonth));
    item.appendChild(row);
    duelMonthList.appendChild(item);
  }
}

function renderMacroColumn(pack, data, other) {
  const col = document.createElement("article");
  col.className = "compareCol";
  const title = document.createElement("h4");
  title.style.color = pack.color;
  title.textContent = pack.label;
  col.appendChild(title);
  if (!data) {
    col.appendChild(document.createTextNode("この月はない"));
    return col;
  }
  const spec = primaryPriceSpec(data.standard || pack.standard);
  const prices = data.prices || {};
  const dl = document.createElement("dl");
  const entries = [
    ["events", (data.events || []).join(" / ")],
    ["population", data.population],
    ["foodYen", data.purchasingPower && data.purchasingPower.foodYenPerCapita],
    [`rice / ${spec.labelJa}`, `${formatNum(prices.ricePrice)} / ${formatNum(prices[spec.field])}`],
    ["primary/rice", data.primaryVsRice],
    ["avgPanic", data.avgPanic],
  ];
  for (const [label, value] of entries) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value == null || value === "" ? "—" : String(value);
    if (other && label === "population" && typeof value === "number" && typeof other.population === "number") {
      const delta = document.createElement("div");
      delta.className = "macroDelta";
      delta.textContent = `差分 ${(value - other.population).toFixed(1)}`;
      dd.appendChild(delta);
    }
    dl.appendChild(dt);
    dl.appendChild(dd);
  }
  col.appendChild(dl);
  return col;
}

function findOpinionAgent(agents, agentId) {
  return (agents || []).find((agent) => agent.agentId === agentId) || null;
}

function renderOpinionTable(views) {
  duelOpinionTable.innerHTML = "";
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["役", duelPacks[0].label, duelPacks[1].label].forEach((text) => {
    const th = document.createElement("th");
    th.textContent = text;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  for (const role of OPINION_ROSTER) {
    const tr = document.createElement("tr");
    const roleCell = document.createElement("td");
    roleCell.textContent = role.label;
    tr.appendChild(roleCell);
    views.forEach((view, index) => {
      const td = document.createElement("td");
      const agent = findOpinionAgent(view && view.opinionAgents, role.id);
      if (!agent || !agent.rumor) {
        td.textContent = "—";
      } else {
        if (agent.intent) {
          const badge = document.createElement("span");
          badge.className = "intentBadge";
          badge.textContent = INTENT_LABELS[agent.intent] || agent.intent;
          td.appendChild(badge);
          td.appendChild(document.createElement("br"));
        }
        td.appendChild(document.createTextNode(agent.rumor));
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  duelOpinionTable.appendChild(table);
}

function findAgriAgent(agents, areaId, roleId) {
  const targetId = `${areaId}_${roleId}`;
  return (agents || []).find((agent) => agent.agentId === targetId || (agent.areaId === areaId && agent.roleId === roleId)) || null;
}

function renderAgriGrid(views) {
  duelAgriGrid.innerHTML = "";
  for (const area of AREA_ORDER) {
    const block = document.createElement("div");
    block.className = "duelAgriArea";
    const title = document.createElement("h5");
    title.textContent = area.label;
    block.appendChild(title);
    for (const role of ROLE_ORDER) {
      const roleBlock = document.createElement("div");
      roleBlock.className = "duelAgriRole";
      const label = document.createElement("div");
      label.className = "roleLabel";
      label.textContent = role.label;
      roleBlock.appendChild(label);
      views.forEach((view, index) => {
        const agent = findAgriAgent(view && view.agriAgents, area.id, role.id);
        const line = document.createElement("div");
        line.style.color = duelPacks[index].color;
        line.textContent = agent && agent.rumor ? agent.rumor : "—";
        roleBlock.appendChild(line);
      });
      block.appendChild(roleBlock);
    }
    duelAgriGrid.appendChild(block);
  }
}

async function showDuelMonth(yearMonth) {
  selectedYearMonth = yearMonth;
  duelDetail.hidden = false;
  duelDetailTitle.textContent = `${yearMonth} — ずんパラ対決`;
  duelMacroGrid.innerHTML = "読み込み中…";
  const views = await Promise.all(
    duelPacks.map((pack) =>
      fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/month/${encodeURIComponent(yearMonth)}`).catch(() => null)
    )
  );
  duelMacroGrid.innerHTML = "";
  duelPacks.forEach((pack, index) => {
    duelMacroGrid.appendChild(renderMacroColumn(pack, views[index], views[1 - index]));
  });
  renderOpinionTable(views);
  renderAgriGrid(views);
  duelDetail.scrollIntoView({ behavior: "smooth", block: "start" });
  for (const item of duelMonthList.querySelectorAll("li")) {
    item.classList.toggle("open", item.dataset.yearMonth === yearMonth);
  }
}

if (duelZipFiles) {
  duelZipFiles.addEventListener("change", () => {
    loadDuelZipFiles(duelZipFiles.files).catch((error) => {
      duelLoadStatus.textContent = String(error.message || error);
    });
  });
}
const duelReloadBtn = document.getElementById("duelReloadBtn");
if (duelReloadBtn) {
  duelReloadBtn.addEventListener("click", () => {
    renderDuelCompare().catch((error) => {
      duelRangeMeta.textContent = String(error.message || error);
    });
  });
}
if (duelOnlyEvents) {
  duelOnlyEvents.addEventListener("change", () => {
    fetchOverlapMonths()
      .then((months) => fillDuelMonthList(months))
      .catch((error) => {
        duelRangeMeta.textContent = String(error.message || error);
      });
  });
}
if (duelOnlyBigChanges) {
  duelOnlyBigChanges.addEventListener("change", () => {
    fetchOverlapMonths()
      .then((months) => fillDuelMonthList(months))
      .catch((error) => {
        duelRangeMeta.textContent = String(error.message || error);
      });
  });
}
