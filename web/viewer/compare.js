const zipFiles = document.getElementById("zipFiles");
const loadStatus = document.getElementById("loadStatus");
const packLegend = document.getElementById("packLegend");
const monthList = document.getElementById("monthList");
const rangeMeta = document.getElementById("rangeMeta");
const onlyEvents = document.getElementById("onlyEvents");
const onlyBigChanges = document.getElementById("onlyBigChanges");
const onlySpeech = document.getElementById("onlySpeech");
const eventLog = document.getElementById("eventLog");
const yearTraceBox = document.getElementById("yearTraceBox");
const lifeRecapBox = document.getElementById("lifeRecapBox");
const chartTooltip = document.getElementById("chartTooltip");
const CHART_PAD_LEFT = 44;
const CHART_PAD_RIGHT = 12;
const CHART_PAD_TOP = 12;
const CHART_PAD_BOTTOM = 28;
const CHART_IDS = ["chartPop", "chartFood", "chartFid", "chartPrice"];
const MAX_COMPARE_RUNS = 6;
const MAX_CHART_MARKERS = 40;
const MARKER_HIT_PX = 14;
const RUN_COLORS = ["#4fc1ff", "#ce9178", "#b5cea8", "#dcdcaa", "#c586c0", "#9cdcfe"];
const MAJOR_EVENT_NEEDLES = [
  "famine",
  "flood",
  "earthquake",
  "eruption",
  "volcano",
  "perry",
  "war_",
  "_war",
  "cholera",
  "covid",
  "tenmei",
  "tenpo",
  "hoei",
  "tsunami",
  "typhoon",
  "kanto",
  "tohoku",
  "sakuradamon",
  "meiji_restoration",
  "taisei_hokan",
  "opium",
  "depression",
  "shogunate_starts",
  "hanshin",
  "atomic",
  "ww2",
  "influenza",
  "pandemic",
];
const MAJOR_NOTE_NEEDLES = [
  "飢饉",
  "噴火",
  "地震",
  "津波",
  "黒船",
  "条約",
  "維新",
  "大戦",
  "戦争",
  "洪水",
  "台風",
  "コレラ",
  "疫病",
  "震災",
  "恐慌",
  "開府",
  "原爆",
  "空襲",
  "一揆",
  "開国",
];
const RUN_COLORS_MARKER = "#dcdcaa";
let loadedPacks = [];
let chartYears = [];
let chartMarkers = [];
let chartLayouts = {};

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function splitEventRef(raw) {
  const text = String(raw || "").trim();
  const cut = text.indexOf(": ");
  if (cut > 0) {
    return { eventId: text.slice(0, cut).trim(), nameJa: text.slice(cut + 2).trim() };
  }
  return { eventId: text, nameJa: "" };
}

function isMajorEvent(eventId, nameJa) {
  const blob = `${eventId} ${nameJa}`.toLowerCase();
  if (MAJOR_EVENT_NEEDLES.some((needle) => blob.includes(needle))) {
    return true;
  }
  return MAJOR_NOTE_NEEDLES.some((needle) => nameJa.includes(needle));
}

function labelsFromEventItem(item) {
  if (Array.isArray(item.labels) && item.labels.length) {
    return item.labels.map((label) => ({
      eventId: String(label.id || ""),
      nameJa: String(label.nameJa || label.id || ""),
    }));
  }
  return (item.events || []).map((raw) => {
    const parsed = splitEventRef(raw);
    return { eventId: parsed.eventId, nameJa: parsed.nameJa || parsed.eventId };
  });
}

function pickChartMarkers(eventItems, serverMarkers) {
  if (Array.isArray(serverMarkers) && serverMarkers.length) {
    return serverMarkers
      .map((item) => ({
        year: Number(item.year),
        yearMonth: String(item.yearMonth || ""),
        eventId: String(item.eventId || ""),
        nameJa: String(item.nameJa || item.eventId || ""),
      }))
      .filter((item) => Number.isFinite(item.year));
  }
  const scored = [];
  for (const item of eventItems) {
    const yearMonth = String(item.yearMonth || "");
    const year = Number(yearMonth.slice(0, 4));
    if (!Number.isFinite(year)) continue;
    for (const label of labelsFromEventItem(item)) {
      if (!isMajorEvent(label.eventId, label.nameJa)) continue;
      scored.push({
        year,
        yearMonth,
        eventId: label.eventId,
        nameJa: label.nameJa,
        weight: label.nameJa.length,
      });
    }
  }
  scored.sort((left, right) => right.weight - left.weight || left.yearMonth.localeCompare(right.yearMonth));
  const byYear = new Map();
  for (const item of scored) {
    if (!byYear.has(item.year)) {
      byYear.set(item.year, item);
    }
    if (byYear.size >= MAX_CHART_MARKERS) break;
  }
  return Array.from(byYear.values()).sort((left, right) => left.year - right.year);
}

function plotX(index, labelCount, plotW) {
  if (labelCount <= 1) return CHART_PAD_LEFT;
  return CHART_PAD_LEFT + (index / (labelCount - 1)) * plotW;
}

function drawLineChart(canvas, labels, seriesList, markers) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const padLeft = CHART_PAD_LEFT;
  const padRight = CHART_PAD_RIGHT;
  const padTop = CHART_PAD_TOP;
  const padBottom = CHART_PAD_BOTTOM;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;
  let minVal = Infinity;
  let maxVal = -Infinity;
  for (const series of seriesList) {
    for (const value of series.data) {
      if (typeof value !== "number") continue;
      if (value < minVal) minVal = value;
      if (value > maxVal) maxVal = value;
    }
  }
  const layout = {
    years: labels.map(Number),
    seriesList,
    minVal,
    maxVal,
    plotW,
    plotH,
    markers: [],
  };
  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || labels.length < 2) {
    ctx.fillStyle = "#9d9d9d";
    ctx.fillText("no series", 8, 20);
    chartLayouts[canvas.id] = layout;
    return;
  }
  if (minVal === maxVal) {
    maxVal = minVal + 1;
    layout.maxVal = maxVal;
  }
  const yearIndex = new Map(layout.years.map((year, index) => [year, index]));
  for (const marker of markers || []) {
    if (!yearIndex.has(marker.year)) continue;
    const index = yearIndex.get(marker.year);
    layout.markers.push({
      ...marker,
      x: plotX(index, labels.length, plotW),
    });
  }
  ctx.save();
  ctx.setLineDash([4, 5]);
  ctx.strokeStyle = "rgba(220, 220, 170, 0.35)";
  for (const marker of layout.markers) {
    ctx.beginPath();
    ctx.moveTo(marker.x, padTop);
    ctx.lineTo(marker.x, padTop + plotH);
    ctx.stroke();
  }
  ctx.restore();
  ctx.strokeStyle = "#3c3c3c";
  ctx.beginPath();
  ctx.moveTo(padLeft, padTop);
  ctx.lineTo(padLeft, padTop + plotH);
  ctx.lineTo(padLeft + plotW, padTop + plotH);
  ctx.stroke();
  ctx.fillStyle = "#9d9d9d";
  ctx.font = "11px sans-serif";
  ctx.fillText(String(maxVal.toFixed(2)), 4, padTop + 8);
  ctx.fillText(String(minVal.toFixed(2)), 4, padTop + plotH);
  ctx.fillText(labels[0], padLeft, height - 6);
  ctx.fillText(labels[labels.length - 1], padLeft + plotW - 32, height - 6);
  seriesList.forEach((series, seriesIndex) => {
    const color = series.color || RUN_COLORS[seriesIndex % RUN_COLORS.length];
    ctx.strokeStyle = color;
    ctx.beginPath();
    let drawing = false;
    series.data.forEach((value, index) => {
      if (typeof value !== "number") {
        drawing = false;
        return;
      }
      const x = plotX(index, labels.length, plotW);
      const y = padTop + plotH - ((value - minVal) / (maxVal - minVal)) * plotH;
      if (!drawing) {
        ctx.moveTo(x, y);
        drawing = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.fillText(series.name, padLeft + 8 + seriesIndex * 140, padTop + 10);
  });
  ctx.fillStyle = RUN_COLORS_MARKER;
  for (const marker of layout.markers) {
    const baseY = padTop + plotH;
    ctx.beginPath();
    ctx.moveTo(marker.x, baseY - 8);
    ctx.lineTo(marker.x - 5, baseY + 2);
    ctx.lineTo(marker.x + 5, baseY + 2);
    ctx.closePath();
    ctx.fill();
  }
  chartLayouts[canvas.id] = layout;
}

function unionYears(seriesPayloads) {
  const yearSet = new Set();
  for (const payload of seriesPayloads) {
    for (const year of (payload.series && payload.series.years) || []) {
      yearSet.add(Number(year));
    }
  }
  return Array.from(yearSet).sort((left, right) => left - right);
}

function alignSeries(years, seriesYears, values) {
  const map = new Map();
  (seriesYears || []).forEach((year, index) => {
    map.set(Number(year), values[index]);
  });
  return years.map((year) => (map.has(year) ? map.get(year) : null));
}

function renderLegend() {
  packLegend.innerHTML = "";
  loadedPacks.forEach((pack) => {
    const chip = document.createElement("span");
    chip.className = "packChip";
    chip.innerHTML = `<span class="packDot" style="background:${pack.color}"></span>${pack.label}`;
    packLegend.appendChild(chip);
  });
}

function formatTipNumber(value) {
  if (typeof value !== "number") return "—";
  if (Math.abs(value) >= 100) return value.toFixed(1);
  return value.toFixed(3);
}

function hideChartTooltip() {
  chartTooltip.hidden = true;
}

function showChartTooltip(event, html) {
  chartTooltip.hidden = false;
  chartTooltip.innerHTML = html;
  const pad = 12;
  let left = event.clientX + pad;
  let top = event.clientY + pad;
  const box = chartTooltip.getBoundingClientRect();
  if (left + box.width > window.innerWidth - 8) {
    left = event.clientX - box.width - pad;
  }
  if (top + box.height > window.innerHeight - 8) {
    top = event.clientY - box.height - pad;
  }
  chartTooltip.style.left = `${Math.max(8, left)}px`;
  chartTooltip.style.top = `${Math.max(8, top)}px`;
}

function canvasLocalX(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  return ((event.clientX - rect.left) / rect.width) * canvas.width;
}

function nearestMarker(layout, localX) {
  let best = null;
  let bestDist = MARKER_HIT_PX;
  for (const marker of layout.markers || []) {
    const dist = Math.abs(marker.x - localX);
    if (dist <= bestDist) {
      best = marker;
      bestDist = dist;
    }
  }
  return best;
}

function jumpToEventLog(yearMonth, year) {
  document.getElementById("yearTrace").value = String(year);
  highlightEventYear(year);
  loadYearTrace().catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
  const hit =
    eventLog.querySelector(`li[data-year-month="${yearMonth}"]`) ||
    eventLog.querySelector(`li[data-year="${year}"]`);
  if (hit) {
    hit.scrollIntoView({ block: "center" });
    hit.classList.add("yearHit");
  }
  const monthHit = yearMonth && monthList.querySelector(`li[data-year-month="${yearMonth}"]`);
  if (monthHit) {
    toggleMonth(monthHit, yearMonth).catch(() => {});
  }
}

async function loadZipFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  if (files.length > MAX_COMPARE_RUNS) {
    throw new Error(`一度に ${MAX_COMPARE_RUNS} 本までなのだ`);
  }
  loadStatus.textContent = "zip を読んでいます…";
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
      color: RUN_COLORS[index % RUN_COLORS.length],
      standard: data.standard,
      span: data.span,
      hasRecap: data.hasRecap,
    });
  }
  loadedPacks = packs;
  renderLegend();
  loadStatus.textContent = `${packs.length} 本を載せたのだ`;
  await renderCompare();
}

async function renderCompare() {
  if (!loadedPacks.length) return;
  const seriesPayloads = [];
  const eventPayloads = [];
  for (const pack of loadedPacks) {
    seriesPayloads.push(await fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/series`));
    eventPayloads.push(await fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/event-log`));
  }
  const years = unionYears(seriesPayloads);
  chartYears = years;
  const labels = years.map(String);
  const mergedEvents = [];
  const serverMarkers = [];
  eventPayloads.forEach((payload, index) => {
    for (const item of payload.events || []) {
      mergedEvents.push({ ...item, packLabel: loadedPacks[index].label, color: loadedPacks[index].color });
    }
    for (const marker of payload.markers || []) {
      serverMarkers.push(marker);
    }
  });
  chartMarkers = pickChartMarkers(mergedEvents, serverMarkers);
  drawLineChart(
    document.getElementById("chartPop"),
    labels,
    loadedPacks.map((pack, index) => ({
      name: pack.label,
      color: pack.color,
      data: alignSeries(years, seriesPayloads[index].series.years, seriesPayloads[index].series.population || []),
    })),
    chartMarkers
  );
  drawLineChart(
    document.getElementById("chartFood"),
    labels,
    loadedPacks.map((pack, index) => ({
      name: pack.label,
      color: pack.color,
      data: alignSeries(years, seriesPayloads[index].series.years, seriesPayloads[index].series.foodYen || []),
    })),
    chartMarkers
  );
  drawLineChart(
    document.getElementById("chartFid"),
    labels,
    loadedPacks.map((pack, index) => ({
      name: pack.label,
      color: pack.color,
      data: alignSeries(years, seriesPayloads[index].series.years, seriesPayloads[index].series.fidelity || []),
    })),
    chartMarkers
  );
  const priceSeries = [];
  loadedPacks.forEach((pack, index) => {
    priceSeries.push({
      name: `${pack.label} 米`,
      color: pack.color,
      data: alignSeries(years, seriesPayloads[index].series.years, seriesPayloads[index].series.ricePrice || []),
    });
    priceSeries.push({
      name: `${pack.label} ずんだ`,
      color: pack.color,
      data: alignSeries(years, seriesPayloads[index].series.years, seriesPayloads[index].series.zundaPrice || []),
    });
  });
  drawLineChart(document.getElementById("chartPrice"), labels, priceSeries, chartMarkers);
  rangeMeta.textContent = loadedPacks
    .map((pack, index) => {
      const payload = seriesPayloads[index];
      const range = Array.isArray(payload.range) ? payload.range.join("..") : payload.range || "";
      return `${pack.label}: ${range} · ${payload.monthCount || "?"}ヶ月`;
    })
    .join("  /  ");
  await fillMonths();
  fillEventLogFromMerged(mergedEvents);
  await fillLifeRecaps();
}

async function fillMonths() {
  const params = new URLSearchParams();
  if (onlyEvents.checked) params.set("onlyEvents", "1");
  if (onlyBigChanges.checked) params.set("onlyBigChanges", "1");
  if (onlySpeech.checked) params.set("onlySpeech", "1");
  const byYm = new Map();
  for (const pack of loadedPacks) {
    const payload = await fetchJson(
      `/api/runs/${encodeURIComponent(pack.stem)}/months?${params.toString()}`
    );
    for (const month of payload.months || []) {
      if (!byYm.has(month.yearMonth)) {
        byYm.set(month.yearMonth, {});
      }
      byYm.get(month.yearMonth)[pack.stem] = month;
    }
  }
  const openYm = monthList.querySelector("li.open")?.dataset.yearMonth || "";
  monthList.innerHTML = "";
  const yearMonths = Array.from(byYm.keys()).sort();
  for (const yearMonth of yearMonths) {
    const item = document.createElement("li");
    item.dataset.yearMonth = yearMonth;
    const row = document.createElement("button");
    row.type = "button";
    row.className = "monthRow";
    const marks = loadedPacks.map((pack) => {
      const month = byYm.get(yearMonth)[pack.stem];
      if (!month) return `${pack.label}: —`;
      const bits = [];
      if (month.eventCount) bits.push(`e${month.eventCount}`);
      if (month.bigChange) bits.push("▲");
      if (month.hasSpeech) bits.push("💬");
      return `${pack.label}: ${bits.join(" ") || "・"}`;
    });
    row.innerHTML = `${yearMonth}<span class="monthMarks">${marks.join(" · ")}</span>`;
    const expand = document.createElement("div");
    expand.className = "monthExpand";
    expand.hidden = true;
    row.addEventListener("click", () => {
      toggleMonth(item, yearMonth).catch((error) => {
        rangeMeta.textContent = String(error.message || error);
      });
    });
    item.appendChild(row);
    item.appendChild(expand);
    monthList.appendChild(item);
  }
  if (openYm) {
    const match = monthList.querySelector(`li[data-year-month="${openYm}"]`);
    if (match) {
      await toggleMonth(match, openYm);
    }
  }
}

function fillMonthColumn(host, data, pack) {
  const col = document.createElement("article");
  col.className = "compareCol";
  const title = document.createElement("h4");
  title.style.color = pack.color;
  title.textContent = pack.label;
  col.appendChild(title);
  if (!data) {
    col.appendChild(document.createTextNode("この月はないのだ"));
    host.appendChild(col);
    return;
  }
  const dl = document.createElement("dl");
  const rows = [
    ["events", (data.events || []).join(" / ")],
    ["population", data.population],
    ["foodYen", data.purchasingPower && data.purchasingPower.foodYenPerCapita],
    ["fidelity", data.fidelity],
    ["rice / zunda", `${(data.prices || {}).ricePrice} / ${(data.prices || {}).zundaPrice}`],
  ];
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value == null || value === "" ? "—" : String(value);
    dl.appendChild(dt);
    dl.appendChild(dd);
  }
  col.appendChild(dl);
  host.appendChild(col);
}

async function toggleMonth(item, yearMonth) {
  const wasOpen = item.classList.contains("open");
  for (const other of monthList.querySelectorAll("li.open")) {
    other.classList.remove("open");
    const panel = other.querySelector(".monthExpand");
    if (panel) panel.hidden = true;
  }
  if (wasOpen) return;
  item.classList.add("open");
  const expand = item.querySelector(".monthExpand");
  expand.hidden = false;
  expand.textContent = "読み込み中…";
  const grid = document.createElement("div");
  grid.className = "compareGrid";
  for (const pack of loadedPacks) {
    let data = null;
    try {
      data = await fetchJson(
        `/api/runs/${encodeURIComponent(pack.stem)}/month/${encodeURIComponent(yearMonth)}`
      );
    } catch (_error) {
      data = null;
    }
    fillMonthColumn(grid, data, pack);
  }
  expand.innerHTML = "";
  expand.appendChild(grid);
}

function fillEventLogFromMerged(merged) {
  merged.sort((left, right) => String(left.yearMonth).localeCompare(String(right.yearMonth)));
  eventLog.innerHTML = "";
  for (const item of merged) {
    const row = document.createElement("li");
    const names = labelsFromEventItem(item)
      .map((label) => (label.nameJa && label.nameJa !== label.eventId ? `${label.eventId}: ${label.nameJa}` : label.eventId))
      .join(" / ");
    row.dataset.year = String(item.yearMonth || "").slice(0, 4);
    row.dataset.yearMonth = String(item.yearMonth || "");
    row.innerHTML = `<span style="color:${item.color}">${item.packLabel || item.label}</span> ${item.yearMonth}  ${names}`;
    row.addEventListener("click", () => {
      const match = monthList.querySelector(`li[data-year-month="${item.yearMonth}"]`);
      if (match) {
        toggleMonth(match, item.yearMonth).catch(() => {});
        match.scrollIntoView({ block: "nearest" });
      }
    });
    eventLog.appendChild(row);
  }
  if (!merged.length) {
    const empty = document.createElement("li");
    empty.textContent = "表示できるイベントはないのだ";
    eventLog.appendChild(empty);
  }
}

async function fillLifeRecaps() {
  lifeRecapBox.innerHTML = "";
  for (const pack of loadedPacks) {
    const col = document.createElement("article");
    col.className = "compareCol";
    const title = document.createElement("h4");
    title.style.color = pack.color;
    title.textContent = pack.label;
    const body = document.createElement("div");
    body.className = "recapBody";
    try {
      const data = await fetchJson(`/api/runs/${encodeURIComponent(pack.stem)}/life-recap`);
      body.textContent = `${data.title || "総括"}${data.source ? ` (${data.source})` : ""}\n\n${data.recap || ""}`;
    } catch (_error) {
      body.textContent = "総括ファイルはこの zip に入っていないのだ";
    }
    col.appendChild(title);
    col.appendChild(body);
    lifeRecapBox.appendChild(col);
  }
}

async function loadYearTrace() {
  const year = document.getElementById("yearTrace").value.trim();
  yearTraceBox.innerHTML = "";
  for (const pack of loadedPacks) {
    const col = document.createElement("article");
    col.className = "compareCol";
    const title = document.createElement("h4");
    title.style.color = pack.color;
    title.textContent = `${pack.label} ${year}`;
    const body = document.createElement("pre");
    try {
      const data = await fetchJson(
        `/api/runs/${encodeURIComponent(pack.stem)}/year/${encodeURIComponent(year)}`
      );
      const lines = (data.months || []).map((month) => {
        const events = (month.events || []).join(" / ");
        const extra = month.decree || "";
        return extra ? `${month.yearMonth}  ${events}  ${extra}` : `${month.yearMonth}  ${events}`;
      });
      body.textContent = lines.join("\n") || "その年の月はないのだ";
    } catch (error) {
      body.textContent = String(error.message || error);
    }
    col.appendChild(title);
    col.appendChild(body);
    yearTraceBox.appendChild(col);
  }
}

function yearIndexFromClick(canvas, event, labelCount) {
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
  const plotW = canvas.width - CHART_PAD_LEFT - CHART_PAD_RIGHT;
  const t = (x - CHART_PAD_LEFT) / plotW;
  const index = Math.round(t * (labelCount - 1));
  return Math.max(0, Math.min(labelCount - 1, index));
}

function highlightEventYear(year) {
  const prefix = String(year);
  for (const row of eventLog.querySelectorAll("li")) {
    row.classList.toggle("yearHit", row.dataset.year === prefix);
  }
}

function bindChartPointer() {
  for (const id of CHART_IDS) {
    const canvas = document.getElementById(id);
    if (!canvas) continue;
    canvas.addEventListener("mousemove", (event) => {
      const layout = chartLayouts[canvas.id];
      if (!layout || layout.years.length < 2) {
        hideChartTooltip();
        return;
      }
      const localX = canvasLocalX(canvas, event);
      const marker = nearestMarker(layout, localX);
      const index = yearIndexFromClick(canvas, event, layout.years.length);
      const year = layout.years[index];
      const lines = [`<strong>${year}</strong>`];
      if (marker) {
        lines.push(`${marker.yearMonth} ${marker.nameJa || marker.eventId}`);
      }
      layout.seriesList.forEach((series) => {
        lines.push(`${series.name}: ${formatTipNumber(series.data[index])}`);
      });
      showChartTooltip(event, lines.join("<br>"));
    });
    canvas.addEventListener("mouseleave", () => hideChartTooltip());
    canvas.addEventListener("click", (event) => {
      const layout = chartLayouts[canvas.id];
      if (!layout || layout.years.length < 2) return;
      const localX = canvasLocalX(canvas, event);
      const marker = nearestMarker(layout, localX);
      if (marker) {
        jumpToEventLog(marker.yearMonth, marker.year);
        return;
      }
      const index = yearIndexFromClick(canvas, event, layout.years.length);
      const year = layout.years[index];
      jumpToEventLog(`${year}-01`, year);
    });
  }
}

zipFiles.addEventListener("change", () => {
  loadZipFiles(zipFiles.files).catch((error) => {
    loadStatus.textContent = String(error.message || error);
  });
});
document.getElementById("reloadBtn").addEventListener("click", () => {
  renderCompare().catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
});
onlyEvents.addEventListener("change", () => renderCompare().catch(() => {}));
onlyBigChanges.addEventListener("change", () => renderCompare().catch(() => {}));
onlySpeech.addEventListener("change", () => renderCompare().catch(() => {}));
document.getElementById("yearTraceBtn").addEventListener("click", () => {
  loadYearTrace().catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
});
bindChartPointer();
