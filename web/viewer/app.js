const runSelect = document.getElementById("runSelect");
const runSearch = document.getElementById("runSearch");
const runList = document.getElementById("runList");
const monthList = document.getElementById("monthList");
const rangeMeta = document.getElementById("rangeMeta");
const jobBox = document.getElementById("jobBox");
const onlyEvents = document.getElementById("onlyEvents");
const onlyBigChanges = document.getElementById("onlyBigChanges");
const onlySpeech = document.getElementById("onlySpeech");
const eventLog = document.getElementById("eventLog");
const jobPopup = document.getElementById("jobPopup");
const busyText = document.getElementById("busyText");
const settingsBox = document.getElementById("settingsBox");
const yearTraceBox = document.getElementById("yearTraceBox");
let jobPollMs = 4000;
let followRunName = "";
let jobWasRunning = false;
let lastViewYm = "";
let chartYears = [];
const CHART_PAD_LEFT = 44;
const CHART_PAD_RIGHT = 12;
const SIM_MIN_YEAR = 1603;
const SIM_MAX_YEAR = 2026;
const SIM_LAST_MONTH = 8;
const DEFAULT_START_YEAR = 1853;
const DEFAULT_START_MONTH = 1;
const DEFAULT_END_YEAR = 1853;
const DEFAULT_END_MONTH = 12;
const CHART_IDS = ["chartPop", "chartFood", "chartFid", "chartPrice"];
const SEC_PER_MINUTE = 60;
const SEC_PER_HOUR = 3600;
const SEC_PER_DAY = 86400;
let cachedRuns = [];

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function drawLineChart(canvas, labels, seriesList) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const padLeft = CHART_PAD_LEFT;
  const padRight = CHART_PAD_RIGHT;
  const padTop = 12;
  const padBottom = 24;
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
  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || labels.length < 2) {
    ctx.fillStyle = "#9d9d9d";
    ctx.fillText("no series", 8, 20);
    return;
  }
  if (minVal === maxVal) {
    maxVal = minVal + 1;
  }
  const colors = ["#4fc1ff", "#ce9178", "#b5cea8"];
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
    ctx.strokeStyle = colors[seriesIndex % colors.length];
    ctx.beginPath();
    series.data.forEach((value, index) => {
      const x = padLeft + (index / (labels.length - 1)) * plotW;
      const y = padTop + plotH - ((value - minVal) / (maxVal - minVal)) * plotH;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = colors[seriesIndex % colors.length];
    ctx.fillText(series.name, padLeft + 8 + seriesIndex * 120, padTop + 10);
  });
}

function formatAgo(mtime) {
  const delta = Math.max(0, Date.now() / 1000 - Number(mtime || 0));
  if (delta < SEC_PER_MINUTE) return "たった今";
  if (delta < SEC_PER_HOUR) return `${Math.floor(delta / SEC_PER_MINUTE)}分前`;
  if (delta < SEC_PER_DAY) return `${Math.floor(delta / SEC_PER_HOUR)}時間前`;
  return `${Math.floor(delta / SEC_PER_DAY)}日前`;
}

function runSearchText(run) {
  return [
    run.stem,
    run.name,
    run.standard,
    run.span,
    run.firstYearMonth,
    run.lastYearMonth,
  ].join(" ").toLowerCase();
}

function renderRunList() {
  if (!runList) return;
  const query = (runSearch && runSearch.value ? runSearch.value : "").trim().toLowerCase();
  const selected = runSelect.value;
  runList.innerHTML = "";
  for (const run of cachedRuns) {
    if (query && !runSearchText(run).includes(query)) continue;
    const card = document.createElement("button");
    card.type = "button";
    card.className = "runCard" + (run.stem === selected ? " isOpen" : "");
    const range = run.span || [run.firstYearMonth, run.lastYearMonth].filter(Boolean).join("..");
    const bits = [];
    if (run.standard) bits.push(String(run.standard));
    if (range) bits.push(range);
    if (run.monthCount) bits.push(`${run.monthCount}ヶ月`);
    if (run.noLlm) bits.push("no-llm");
    if (run.hasRecap) bits.push("総括あり");
    card.innerHTML = `<strong>${run.stem}</strong><span class="runMeta">${formatAgo(run.mtime)}</span><span class="runBits">${bits.join(" · ")}</span>`;
    card.addEventListener("click", () => {
      runSelect.value = run.stem;
      renderRunList();
      loadView().catch((error) => {
        rangeMeta.textContent = String(error.message || error);
      });
    });
    runList.appendChild(card);
  }
  if (!runList.childElementCount) {
    runList.textContent = cachedRuns.length ? "見つからんのだ" : "ランがまだないのだ";
  }
}

async function loadRuns(preferredStem) {
  const data = await fetchJson("/api/runs");
  cachedRuns = data.runs || [];
  const previous = preferredStem || runSelect.value;
  runSelect.innerHTML = "";
  for (const run of cachedRuns) {
    const option = document.createElement("option");
    option.value = run.stem;
    const preset = (run.presets && run.presets[0]) || "";
    option.textContent = preset ? `${run.name} (${preset})` : run.name;
    runSelect.appendChild(option);
  }
  const names = Array.from(runSelect.options).map((item) => item.value);
  if (previous && names.includes(previous)) {
    runSelect.value = previous;
  }
  renderRunList();
}

async function exportCurrentRun() {
  const stem = runSelect.value;
  if (!stem) return;
  const response = await fetch(`/api/runs/${encodeURIComponent(stem)}/export`);
  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      message = data.error || message;
    } catch (_err) {
      /* zip error body is json */
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${stem}.zip`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function importRunFile(file) {
  const response = await fetch(`/api/runs/import?filename=${encodeURIComponent(file.name)}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: file,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  await showRun(data.stem);
}

async function showRun(stem) {
  await loadRuns(stem);
  if (stem) runSelect.value = stem;
  await loadView();
}

async function loadView() {
  const stem = runSelect.value;
  if (!stem) return;
  const series = await fetchJson(`/api/runs/${encodeURIComponent(stem)}/series`);
  const years = (series.series && series.series.years) || [];
  chartYears = years.map(Number);
  const labels = years.map(String);
  drawLineChart(document.getElementById("chartPop"), labels, [
    { name: "population", data: series.series.population || [] },
  ]);
  drawLineChart(document.getElementById("chartFood"), labels, [
    { name: "foodYenPerCapita", data: series.series.foodYen || [] },
  ]);
  drawLineChart(document.getElementById("chartFid"), labels, [
    { name: "fidelity", data: series.series.fidelity || [] },
  ]);
  drawLineChart(document.getElementById("chartPrice"), labels, [
    { name: "ricePrice", data: series.series.ricePrice || [] },
    { name: "zundaPrice", data: series.series.zundaPrice || [] },
  ]);
  rangeMeta.textContent = `${series.range || ""} · ${series.monthCount || ""} months · ${series.method || ""}`;
  const params = new URLSearchParams();
  if (onlyEvents.checked) params.set("onlyEvents", "1");
  if (onlyBigChanges.checked) params.set("onlyBigChanges", "1");
  if (onlySpeech.checked) params.set("onlySpeech", "1");
  const monthsPayload = await fetchJson(
    `/api/runs/${encodeURIComponent(stem)}/months?${params.toString()}`
  );
  const openYm = monthList.querySelector("li.open")?.dataset.yearMonth || "";
  monthList.innerHTML = "";
  for (const month of monthsPayload.months) {
    const item = document.createElement("li");
    item.dataset.yearMonth = month.yearMonth;
    const row = document.createElement("button");
    row.type = "button";
    row.className = "monthRow";
    const events = month.eventCount ? ` events=${month.eventCount}` : "";
    const mark = month.bigChange ? " ▲" : "";
    const talk = month.hasSpeech ? " 💬" : "";
    const eventIds = (month.events || []).join(",");
    row.textContent = `${month.yearMonth}${events}${mark}${talk}  ${eventIds ? `[${eventIds}] ` : ""}${month.blurb || ""}`;
    const expand = document.createElement("div");
    expand.className = "monthExpand";
    expand.hidden = true;
    row.addEventListener("click", () => toggleMonth(stem, item, month.yearMonth));
    item.appendChild(row);
    item.appendChild(expand);
    monthList.appendChild(item);
  }
  if (openYm) {
    const match = monthList.querySelector(`li[data-year-month="${openYm}"]`);
    if (match) {
      await toggleMonth(stem, match, openYm);
    }
  }
  await fillEventLog(stem);
  await fillLifeRecap(stem);
}

async function fillLifeRecap(stem) {
  const box = document.getElementById("lifeRecapBox");
  if (!box) return;
  try {
    const data = await fetchJson(`/api/runs/${encodeURIComponent(stem)}/life-recap`);
    const title = data.title || "総括";
    const source = data.source ? ` (${data.source})` : "";
    box.textContent = `${title}${source}\n\n${data.recap || ""}`;
  } catch (_error) {
    box.textContent = "まだ総括がありません。ラン完了後に自動で付きます。ボタンで作り直せます。";
  }
}

async function generateLifeRecap() {
  const stem = runSelect.value;
  const box = document.getElementById("lifeRecapBox");
  if (!stem || !box) return;
  box.textContent = "総括を書いています…";
  const data = await fetchJson(`/api/runs/${encodeURIComponent(stem)}/life-recap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ useLlm: !document.getElementById("noLlm").checked }),
  });
  box.textContent = `${data.title || "総括"} (${data.source || ""})\n\n${data.recap || ""}`;
}

async function fillEventLog(stem) {
  const payload = await fetchJson(`/api/runs/${encodeURIComponent(stem)}/event-log`);
  eventLog.innerHTML = "";
  for (const item of payload.events || []) {
    const row = document.createElement("li");
    row.textContent = `${item.yearMonth}  ${(item.events || []).join(", ")}`;
    row.dataset.year = String(item.yearMonth || "").slice(0, 4);
    row.addEventListener("click", () => {
      const match = monthList.querySelector(`li[data-year-month="${item.yearMonth}"]`);
      if (match) {
        toggleMonth(stem, match, item.yearMonth);
        match.scrollIntoView({ block: "nearest" });
      }
    });
    eventLog.appendChild(row);
  }
  if (!(payload.events || []).length) {
    const empty = document.createElement("li");
    empty.textContent = "このランに表示できるイベントはありません";
    eventLog.appendChild(empty);
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

async function jumpToYear(year) {
  document.getElementById("yearTrace").value = String(year);
  await loadYearTrace();
  highlightEventYear(year);
  const heading = document.getElementById("eventLog");
  heading.scrollIntoView({ behavior: "smooth", block: "start" });
}

function bindChartClicks() {
  for (const id of CHART_IDS) {
    const canvas = document.getElementById(id);
    if (!canvas) continue;
    canvas.addEventListener("mousemove", (event) => {
      if (chartYears.length < 2) return;
      const index = yearIndexFromClick(canvas, event, chartYears.length);
      canvas.title = `${chartYears[index]} 年へ`;
    });
    canvas.addEventListener("click", (event) => {
      if (chartYears.length < 2) return;
      const index = yearIndexFromClick(canvas, event, chartYears.length);
      jumpToYear(chartYears[index]).catch((error) => {
        rangeMeta.textContent = String(error.message || error);
      });
    });
  }
}

const ROLE_SELECT_IDS = {
  ruler: "roleRuler",
  crowd: "roleCrowd",
  mascot: "roleMascot",
  opinion: "roleOpinion",
  agri: "roleAgri",
};

function collectModelIds(payload) {
  const ids = new Set();
  for (const modelId of payload.openai?.modelIds || []) {
    if (modelId) ids.add(String(modelId));
  }
  for (const item of payload.lmStudio?.data || []) {
    if (item && item.id) ids.add(String(item.id));
  }
  for (const hint of payload.localHints || []) {
    if (hint) ids.add(String(hint));
  }
  for (const modelId of Object.values(payload.roles || {})) {
    if (modelId) ids.add(String(modelId));
  }
  return Array.from(ids).sort();
}

function fillRoleSelects(modelIds, selectedRoles) {
  const roles = selectedRoles || {};
  for (const [role, elementId] of Object.entries(ROLE_SELECT_IDS)) {
    const select = document.getElementById(elementId);
    const current = String(roles[role] || select.value || "");
    select.innerHTML = "";
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "（未選択）";
    select.appendChild(blank);
    const seen = new Set();
    for (const modelId of modelIds) {
      if (!modelId || seen.has(modelId)) continue;
      seen.add(modelId);
      const option = document.createElement("option");
      option.value = modelId;
      option.textContent = modelId;
      select.appendChild(option);
    }
    if (current && !seen.has(current)) {
      const option = document.createElement("option");
      option.value = current;
      option.textContent = current;
      select.appendChild(option);
    }
    select.value = current;
  }
}

async function toggleMonth(stem, item, yearMonth) {
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
  await openMonth(stem, yearMonth, expand);
}

const METRIC_HINTS = {
  events: "その月に発火したイベント ID。riot_risk は一覧から除外。",
  decree: "為政者（ruler）が出した布告文。",
  rulerReason: "布告の理由。LLM ならモデル、なければルール。",
  mascot: "マスコットの一言。crowd 役のモデル、または定型。",
  mood: "民衆ムードの短文。",
  rumor: "市中の噂。",
  population: "マクロ人口。出生・死亡・移動の月次更新。",
  foodYen: "時代バスケット円 × 在庫月数/6。kg直換算ではない。",
  fidelity: "史実との近さ。米35%・金銀25%・正統性20%・人口20%の誤差を1から引く。",
  "rice / zunda": "sim 相対価格。米1.0 ≒ 1kg相当。円は PPP 側。",
};

function addDl(dl, label, value) {
  const dt = document.createElement("dt");
  dt.textContent = label;
  const hint = METRIC_HINTS[label];
  if (hint) {
    dt.title = hint;
    const mark = document.createElement("span");
    mark.className = "why";
    mark.textContent = " ?";
    mark.title = hint;
    dt.appendChild(mark);
  }
  const dd = document.createElement("dd");
  dd.textContent = value == null || value === "" ? "—" : String(value);
  if (hint) dd.title = hint;
  dl.appendChild(dt);
  dl.appendChild(dd);
}

function fillMonthDetail(host, data, yearMonth) {
  host.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = yearMonth;
  host.appendChild(title);
  const dl = document.createElement("dl");
  addDl(dl, "events", (data.events || []).join(", "));
  addDl(dl, "decree", data.decree);
  addDl(dl, "rulerReason", data.rulerReason);
  addDl(dl, "mascot", `${data.mascotId || ""} ${data.mascotSpeech || ""}`);
  addDl(dl, "mood", data.moodText);
  addDl(dl, "rumor", data.rumor);
  addDl(dl, "population", data.population);
  addDl(dl, "foodYen", data.purchasingPower && data.purchasingPower.foodYenPerCapita);
  addDl(dl, "fidelity", data.fidelity);
  addDl(dl, "rice / zunda", `${(data.prices || {}).ricePrice} / ${(data.prices || {}).zundaPrice}`);
  host.appendChild(dl);
  for (const agent of data.opinionAgents || []) {
    const block = document.createElement("div");
    block.className = "opinion";
    block.textContent = `${agent.agentId || ""} [${agent.intent || ""}] ${agent.rumor || ""}`;
    host.appendChild(block);
  }
}

async function openMonth(stem, yearMonth, expand) {
  const data = await fetchJson(
    `/api/runs/${encodeURIComponent(stem)}/month/${encodeURIComponent(yearMonth)}`
  );
  fillMonthDetail(expand, data, yearMonth);
}

function renderSplitPlan(host, lanes) {
  if (!host) return;
  host.innerHTML = "";
  if (!lanes || !lanes.length) return;
  for (const lane of lanes) {
    const card = document.createElement("article");
    card.className = "splitLane splitLane-" + (lane.lane || "");
    const heading = document.createElement("h3");
    heading.textContent = lane.title || lane.lane || "レーン";
    const blurb = document.createElement("p");
    blurb.className = "hint";
    const simBit = lane.simModel ? ` シミュが呼ぶ名前: ${lane.simRole || ""} = ${lane.simModel}` : "";
    blurb.textContent = (lane.blurb || "") + simBit;
    const table = document.createElement("ul");
    table.className = "splitTasks";
    for (const task of lane.tasks || []) {
      const row = document.createElement("li");
      if (task.present === true) row.className = "isPresent";
      if (task.present === false) row.className = "isMissing";
      const how = document.createElement("span");
      how.className = "splitHow";
      how.textContent = task.how || "";
      const label = document.createElement("span");
      label.className = "splitLabel";
      label.textContent = task.label || task.id || "";
      const model = document.createElement("code");
      model.textContent = task.modelId || "";
      row.appendChild(how);
      row.appendChild(label);
      row.appendChild(model);
      if (task.present === true || task.present === false) {
        const badge = document.createElement("span");
        badge.className = "modelStatus " + (task.present ? "present" : "missing");
        badge.textContent = task.present ? "ある" : "ない";
        row.appendChild(badge);
      }
      table.appendChild(row);
    }
    card.appendChild(heading);
    card.appendChild(blurb);
    card.appendChild(table);
    host.appendChild(card);
  }
}

async function fillSettings() {
  const data = await fetchJson("/api/settings");
  document.getElementById("provider").value = data.provider || "lmstudio";
  document.getElementById("lmStudioHost").value = data.lmStudioHost || "";
  document.getElementById("lmStudioPort").value = String(data.lmStudioPort || "1234");
  document.getElementById("openaiBaseUrl").value = data.openaiBaseUrl || "";
  document.getElementById("openaiApiKey").value = "";
  const hint = document.getElementById("gatewayHint");
  if (hint) hint.textContent = data.gatewayHint || "";
  fillRoleSelects(Object.values(data.roles || {}), data.roles);
  renderSplitPlan(document.getElementById("splitPlanBox"), data.splitPlan);
  settingsBox.textContent = JSON.stringify(data, null, 2);
  refreshSplitInventory().catch(() => {});
}

async function refreshSplitInventory() {
  const data = await fetchJson("/api/settings/gateway-default");
  if (data.splitPlan && data.splitPlan.length) {
    renderSplitPlan(document.getElementById("splitPlanBox"), data.splitPlan);
  }
}

async function probeModels() {
  const data = await fetchJson("/api/models");
  settingsBox.textContent = JSON.stringify(data, null, 2);
  fillRoleSelects(collectModelIds(data), settingsPayload().roles);
}

function settingsPayload() {
  return {
    provider: document.getElementById("provider").value,
    lmStudioHost: document.getElementById("lmStudioHost").value.trim(),
    lmStudioPort: document.getElementById("lmStudioPort").value.trim(),
    openaiBaseUrl: document.getElementById("openaiBaseUrl").value.trim(),
    openaiApiKey: document.getElementById("openaiApiKey").value,
    roles: {
      ruler: document.getElementById("roleRuler").value.trim(),
      crowd: document.getElementById("roleCrowd").value.trim(),
      mascot: document.getElementById("roleMascot").value.trim(),
      opinion: document.getElementById("roleOpinion").value.trim(),
      agri: document.getElementById("roleAgri").value.trim(),
    },
  };
}

async function saveSettings() {
  const data = await fetchJson("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settingsPayload()),
  });
  document.getElementById("openaiApiKey").value = "";
  settingsBox.textContent = JSON.stringify(data, null, 2);
}

function closeGatewayDefaultPopup() {
  document.getElementById("defaultPresetPopup").hidden = true;
}

async function openGatewayDefaultPopup() {
  const summary = document.getElementById("defaultPresetSummary");
  const list = document.getElementById("defaultPresetList");
  const okBtn = document.getElementById("defaultPresetOkBtn");
  summary.textContent = "LM Studio のカタログを探しています…";
  summary.className = "presetSummary";
  list.innerHTML = "";
  document.getElementById("defaultPresetPopup").hidden = false;
  let data;
  try {
    data = await fetchJson("/api/settings/gateway-default");
  } catch (error) {
    summary.textContent = `探せていません: ${error.message || error}`;
    summary.className = "presetSummary isMissing";
    return;
  }
  const requiredPresent = Number(data.requiredPresent || 0);
  const requiredTotal = Number(data.requiredTotal || 0);
  const optionalPresent = Number(data.optionalPresent || 0);
  const optionalTotal = Number(data.optionalTotal || 0);
  if (!data.probeSource) {
    summary.textContent = `探せていません。LM Studio（:1234）かゲートウェイ（:4000）を起動して、もう一度開いてください。${data.probeError || ""}`;
    summary.className = "presetSummary isMissing";
  } else if (data.ready) {
    summary.textContent = `必須 ${requiredPresent}/${requiredTotal} そろった（${data.probeSource}）。任意 ${optionalPresent}/${optionalTotal}。`;
    summary.className = "presetSummary isReady";
  } else {
    summary.textContent = `必須が足りない ${requiredPresent}/${requiredTotal}（${data.probeSource}）。ない必須を Discover から入れて、もう一度開いてください。`;
    summary.className = "presetSummary isMissing";
  }
  renderSplitPlan(document.getElementById("defaultPresetSplit"), data.splitPlan);
  for (const item of data.downloadList || []) {
    const row = document.createElement("li");
    row.className = item.present ? "isPresent" : "isMissing";
    const badge = document.createElement("span");
    badge.className = "modelStatus " + (item.present ? "present" : "missing");
    badge.textContent = item.present ? "ある" : "ない";
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `${item.required ? "必須" : "任意"} · ${item.id}`;
    const purpose = document.createElement("span");
    purpose.className = "modelPurpose";
    purpose.textContent = item.purpose || "";
    body.appendChild(title);
    body.appendChild(purpose);
    if (item.present && item.matchedId && item.matchedId !== item.id) {
      const matched = document.createElement("span");
      matched.className = "modelMatched";
      matched.textContent = `一致: ${item.matchedId}`;
      body.appendChild(matched);
    }
    row.appendChild(badge);
    row.appendChild(body);
    list.appendChild(row);
  }
  okBtn.disabled = false;
}

async function confirmGatewayDefault() {
  await fetchJson("/api/settings/apply-gateway-default", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  closeGatewayDefaultPopup();
  await fillSettings();
}

async function loadYearTrace() {
  const stem = runSelect.value;
  const year = document.getElementById("yearTrace").value.trim();
  if (!stem || !year) return;
  const data = await fetchJson(`/api/runs/${encodeURIComponent(stem)}/year/${encodeURIComponent(year)}`);
  yearTraceBox.innerHTML = "";
  for (const month of data.months || []) {
    const block = document.createElement("div");
    block.className = "year-month";
    const speech = month.mascotSpeech || "";
    const decree = month.decree || "";
    const rumor = month.rumor || "";
    const opinions = (month.opinionAgents || [])
      .map((agent) => `${agent.agentId || ""}:${agent.intent || ""} ${agent.rumor || ""}`)
      .join(" / ");
    block.textContent = `${month.yearMonth} 布告:${decree} ずんだ:${speech} 噂:${rumor} 世論:${opinions}`;
    yearTraceBox.appendChild(block);
  }
  if (!(data.months || []).length) {
    yearTraceBox.textContent = "その年の月がありません";
  }
}

async function refreshJob() {
  const data = await fetchJson("/api/job");
  jobBox.textContent = JSON.stringify(data, null, 2);
  const runName = data.runName || followRunName;
  if (data.running) {
    followRunName = runName;
    jobWasRunning = true;
    jobPopup.hidden = false;
    document.body.classList.add("jobRunning");
    const ym = data.currentYearMonth || "…";
    busyText.textContent = `推論中 ${ym} · ${runName || ""} · ${data.started || ""}`;
    jobPollMs = 1500;
    if (runName && ym !== lastViewYm) {
      lastViewYm = ym;
      await showRun(runName).catch(() => {});
    }
  } else {
    jobPopup.hidden = true;
    document.body.classList.remove("jobRunning");
    jobPollMs = 4000;
    if (jobWasRunning && followRunName) {
      jobWasRunning = false;
      lastViewYm = "";
      await showRun(followRunName).catch(() => {});
      document.getElementById("viewPane").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
}

async function stopRun() {
  try {
    const data = await fetchJson("/api/job/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    jobBox.textContent = JSON.stringify(data, null, 2);
    if (!data.running) {
      jobPopup.hidden = true;
      document.body.classList.remove("jobRunning");
    }
  } catch (error) {
    jobBox.textContent = String(error.message || error);
  }
}

function padMonth(month) {
  return String(month).padStart(2, "0");
}

function maxMonthForYear(year) {
  return Number(year) >= SIM_MAX_YEAR ? SIM_LAST_MONTH : 12;
}

function fillYearOptions(select, selectedYear) {
  select.innerHTML = "";
  for (let year = SIM_MIN_YEAR; year <= SIM_MAX_YEAR; year += 1) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = String(year);
    select.appendChild(option);
  }
  select.value = String(selectedYear);
}

function fillMonthOptions(select, year, selectedMonth) {
  const maxMonth = maxMonthForYear(year);
  const month = Math.min(Number(selectedMonth) || 1, maxMonth);
  select.innerHTML = "";
  for (let n = 1; n <= maxMonth; n += 1) {
    const option = document.createElement("option");
    option.value = String(n);
    option.textContent = padMonth(n);
    select.appendChild(option);
  }
  select.value = String(month);
}

function yearMonthValue(yearId, monthId) {
  const year = document.getElementById(yearId).value;
  const month = padMonth(document.getElementById(monthId).value);
  return year + "-" + month;
}

function clampSpanOrder() {
  const start = yearMonthValue("startYear", "startMonth");
  const end = yearMonthValue("endYear", "endMonth");
  if (end >= start) return;
  document.getElementById("endYear").value = document.getElementById("startYear").value;
  fillMonthOptions(
    document.getElementById("endMonth"),
    document.getElementById("endYear").value,
    document.getElementById("startMonth").value,
  );
}

function onSpanYearChange(yearId, monthId) {
  const yearSelect = document.getElementById(yearId);
  const monthSelect = document.getElementById(monthId);
  fillMonthOptions(monthSelect, yearSelect.value, monthSelect.value);
  clampSpanOrder();
}

function initSpanPickers() {
  fillYearOptions(document.getElementById("startYear"), DEFAULT_START_YEAR);
  fillYearOptions(document.getElementById("endYear"), DEFAULT_END_YEAR);
  fillMonthOptions(document.getElementById("startMonth"), DEFAULT_START_YEAR, DEFAULT_START_MONTH);
  fillMonthOptions(document.getElementById("endMonth"), DEFAULT_END_YEAR, DEFAULT_END_MONTH);
  document.getElementById("startYear").addEventListener("change", () => {
    onSpanYearChange("startYear", "startMonth");
  });
  document.getElementById("endYear").addEventListener("change", () => {
    onSpanYearChange("endYear", "endMonth");
  });
  document.getElementById("startMonth").addEventListener("change", clampSpanOrder);
  document.getElementById("endMonth").addEventListener("change", clampSpanOrder);
}

async function launchRun() {
  const payload = {
    standard: document.getElementById("standard").value,
    start: yearMonthValue("startYear", "startMonth"),
    end: yearMonthValue("endYear", "endMonth"),
    runName: document.getElementById("runName").value.trim(),
    noLlm: document.getElementById("noLlm").checked,
    historicalPolicy: document.getElementById("historicalPolicy").checked,
    resume: document.getElementById("resume").checked,
    confirmFullSpan: document.getElementById("confirmFullSpan").checked,
  };
  try {
    const data = await fetchJson("/api/job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    jobBox.textContent = JSON.stringify(data, null, 2);
    followRunName = payload.runName;
    jobWasRunning = true;
    lastViewYm = "";
    jobPopup.hidden = false;
    document.body.classList.add("jobRunning");
    busyText.textContent = `起動した ${data.currentYearMonth || data.started || ""}`;
    await showRun(payload.runName).catch(() => {});
  } catch (error) {
    jobBox.textContent = String(error.message || error);
  }
}

document.getElementById("reloadBtn").addEventListener("click", () => {
  loadView().catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
});
onlyEvents.addEventListener("change", () => loadView().catch(() => {}));
onlyBigChanges.addEventListener("change", () => loadView().catch(() => {}));
onlySpeech.addEventListener("change", () => loadView().catch(() => {}));
runSelect.addEventListener("change", () => {
  renderRunList();
  loadView().catch(() => {});
});
if (runSearch) {
  runSearch.addEventListener("input", renderRunList);
}
document.getElementById("exportBtn").addEventListener("click", () => {
  exportCurrentRun().catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
});
document.getElementById("importFile").addEventListener("change", (event) => {
  const file = event.target.files && event.target.files[0];
  event.target.value = "";
  if (!file) return;
  importRunFile(file).catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
});
document.getElementById("fillResumeBtn").addEventListener("click", () => {
  const stem = runSelect.value;
  if (stem) {
    document.getElementById("runName").value = stem;
  }
  document.getElementById("resume").checked = true;
  document.getElementById("confirmFullSpan").checked = true;
});
document.getElementById("launchBtn").addEventListener("click", launchRun);
document.getElementById("stopBtn").addEventListener("click", stopRun);
document.getElementById("busyStopBtn").addEventListener("click", stopRun);
document.getElementById("saveSettingsBtn").addEventListener("click", () => {
  saveSettings().catch((error) => {
    settingsBox.textContent = String(error.message || error);
  });
});
document.getElementById("probeBtn").addEventListener("click", () => {
  probeModels().catch((error) => {
    settingsBox.textContent = String(error.message || error);
  });
});
document.getElementById("applyGatewayDefaultBtn").addEventListener("click", () => {
  openGatewayDefaultPopup().catch((error) => {
    settingsBox.textContent = String(error.message || error);
  });
});
document.getElementById("defaultPresetCancelBtn").addEventListener("click", closeGatewayDefaultPopup);
document.getElementById("defaultPresetOkBtn").addEventListener("click", () => {
  confirmGatewayDefault().catch((error) => {
    settingsBox.textContent = String(error.message || error);
  });
});
document.getElementById("yearTraceBtn").addEventListener("click", () => {
  loadYearTrace().catch((error) => {
    yearTraceBox.textContent = String(error.message || error);
  });
});
document.getElementById("recapBtn").addEventListener("click", () => {
  generateLifeRecap().catch((error) => {
    const box = document.getElementById("lifeRecapBox");
    if (box) box.textContent = String(error.message || error);
  });
});

function pollJob() {
  refreshJob()
    .catch(() => {})
    .finally(() => {
      setTimeout(pollJob, jobPollMs);
    });
}

bindChartClicks();
initSpanPickers();
fillSettings()
  .then(loadRuns)
  .then(loadView)
  .then(refreshJob)
  .then(pollJob)
  .then(() => probeModels().catch((error) => {
    settingsBox.textContent = String(error.message || error);
  }))
  .catch((error) => {
    rangeMeta.textContent = String(error.message || error);
  });
