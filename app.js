const SUPABASE_URL = (window.SUPABASE_URL || "").replace(/\/$/, "");
const SUPABASE_KEY = window.SUPABASE_ANON_KEY || "";

async function supabaseInsert(table, record) {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "apikey": SUPABASE_KEY,
      "Authorization": `Bearer ${SUPABASE_KEY}`,
      "Prefer": "return=minimal"
    },
    body: JSON.stringify(record)
  });
  if (!response.ok) throw new Error(`Supabase ${table}: ${await response.text()}`);
  return true;
}

const STORAGE_KEY = "comboio-fuel-records";
const RECEIPTS_STORAGE_KEY = "comboio-fuel-receipts";
const PENDING_SYNC_STORAGE_KEY = "comboio-pending-sync-events";
const ORDER_SEQ_KEY = "comboio-order-seq";
const DIESEL_ENTRIES_KEY = "comboio-diesel-entries";
const POST_FUEL_OPTIONS = ["Gasolina Comum","Etanol Comum","Diesel S-10","Diesel S-500 Aditivado","Diesel S-500 Comum"];
const RECEIPT_FUEL_OPTIONS = [...POST_FUEL_OPTIONS];

const form = document.getElementById("fuel-form");
const receiptForm = document.getElementById("receipt-form");
const workspacePosto = document.getElementById("workspace-posto");
const workspaceComboio = document.getElementById("workspace-comboio");
const trailingConfig = document.getElementById("trailing-config");
const trailingInforme = document.getElementById("trailing-informe");
const trailingDiesel = document.getElementById("trailing-diesel");
const gateScreen = document.getElementById("gate-screen");
const appScreen = document.getElementById("app-screen");
const gatePostoButton = document.getElementById("gate-posto");
const gateComboioButton = document.getElementById("gate-comboio");
const changeAreaButton = document.getElementById("change-area");
const areaLabel = document.getElementById("area-label");
const appWorkflowHeading = document.getElementById("app-workflow-heading");
const appWorkflowSub = document.getElementById("app-workflow-sub");
const DOCUMENT_TITLE_DEFAULT = "CONTROLE DE ABASTECIMENTO DE FROTA";
const fuelDateTimeInput = document.getElementById("fuelDateTime");
const receiptDateTimeInput = document.getElementById("receiptDateTime");
const recentPostoList = document.getElementById("recent-posto-list");
const recentComboioList = document.getElementById("recent-comboio-list");
const nextOrderPreview = document.getElementById("next-order-preview");
const connectionStatus = document.getElementById("connection-status");
const dbSyncStatus = document.getElementById("db-sync-status");
const fuelTypeSelect = document.getElementById("fuelType");
const receiptFuelTypeSelect = document.getElementById("receiptFuelType");
const fuelSettingsForm = document.getElementById("fuel-settings-form");
const newFuelOptionInput = document.getElementById("new-fuel-option");
const fuelOptionsList = document.getElementById("fuel-options-list");
const lubeObservationWrap = document.getElementById("lube-observation-wrap");
const lubeObservationInput = document.getElementById("lubeObservation");
const secaoCombustivel = document.getElementById("secao-combustivel");
const secaoLubrificacao = document.getElementById("secao-lubrificacao");

function getTipoServico() {
  const c = receiptForm.querySelector('input[name="tipoServico"]:checked');
  return c ? c.value : "abastecimento";
}

function atualizarSecoesPorTipo() {
  const tipo = getTipoServico();
  const isLub = tipo === "lubrificacao";
  const isAbast = tipo === "abastecimento";
  secaoCombustivel.classList.toggle("hidden", isLub);
  receiptFuelTypeSelect.required = !isLub;
  document.getElementById("receiptLiters").required = !isLub;
  secaoLubrificacao.classList.toggle("hidden", isAbast);
}

receiptForm.querySelectorAll('input[name="tipoServico"]').forEach((r) => {
  r.addEventListener("change", () => { atualizarSecoesPorTipo(); toggleLubeObservationField(); });
});

function attachTrailingBlocks(mode) {
  if (mode === "posto") {
    workspacePosto.appendChild(trailingConfig);
    workspacePosto.appendChild(trailingInforme);
  } else {
    workspaceComboio.appendChild(trailingDiesel);
    workspaceComboio.appendChild(trailingConfig);
    workspaceComboio.appendChild(trailingInforme);
  }
}

function showGate() {
  document.title = DOCUMENT_TITLE_DEFAULT;
  gateScreen.classList.remove("hidden");
  appScreen.classList.add("hidden");
  window.scrollTo(0, 0);
}

function enterWorkspace(mode) {
  gateScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
  const isPosto = mode === "posto";
  workspacePosto.classList.toggle("hidden", !isPosto);
  workspaceComboio.classList.toggle("hidden", isPosto);
  attachTrailingBlocks(mode);
  if (!isPosto) { updateOrderPreview(); atualizarSecoesPorTipo(); renderDieselSaldo(); }
  areaLabel.textContent = isPosto ? "Fluxo do posto. Nada do comboio nesta tela." : "Fluxo do comboio. Nada do posto nesta tela.";
  if (appWorkflowHeading && appWorkflowSub) {
    appWorkflowHeading.textContent = isPosto ? "Posto de abastecimento" : "Comboio";
    appWorkflowSub.textContent = isPosto ? "Voce escolheu posto no inicio." : "Voce escolheu comboio no inicio.";
  }
  document.title = isPosto ? "Posto | Abastecimento frota" : "Comboio | Abastecimento frota";
  fillFuelSelects(); renderFuelOptionsSettings(); window.scrollTo(0, 0);
}

function getNowLocalDateTimeInputValue() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function toIsoFromDateTimeLocal(value) {
  if (!value) return new Date().toISOString();
  const d = new Date(value);
  return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
}

function setDefaultDateTimes() {
  if (!fuelDateTimeInput.value) fuelDateTimeInput.value = getNowLocalDateTimeInputValue();
  if (!receiptDateTimeInput.value) receiptDateTimeInput.value = getNowLocalDateTimeInputValue();
}

function peekNextOrderNumber() {
  const n = Number(localStorage.getItem(ORDER_SEQ_KEY) || "0") + 1;
  return `COM-${String(n).padStart(5, "0")}`;
}

function assignNextOrderNumber() {
  const n = Number(localStorage.getItem(ORDER_SEQ_KEY) || "0") + 1;
  localStorage.setItem(ORDER_SEQ_KEY, String(n));
  return `COM-${String(n).padStart(5, "0")}`;
}

function updateOrderPreview() {
  nextOrderPreview.textContent = `Proxima ordem ao salvar: ${peekNextOrderNumber()}`;
}

function toggleLubeObservationField() {
  const tipo = getTipoServico();
  if (tipo === "abastecimento") { lubeObservationWrap.classList.add("hidden"); lubeObservationInput.required = false; return; }
  const actions = [...receiptForm.querySelectorAll('input[name="lubeActions"]:checked')].map(n => n.value);
  const req = actions.includes("corretiva") || actions.includes("completar_nivel");
  lubeObservationWrap.classList.toggle("hidden", !req);
  lubeObservationInput.required = req;
  if (!req) lubeObservationInput.value = "";
}

function makeId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

function getRecords() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); } catch { return []; } }
function saveRecords(r) { localStorage.setItem(STORAGE_KEY, JSON.stringify(r)); }
function getReceipts() { try { return JSON.parse(localStorage.getItem(RECEIPTS_STORAGE_KEY) || "[]"); } catch { return []; } }
function saveReceipts(r) { localStorage.setItem(RECEIPTS_STORAGE_KEY, JSON.stringify(r)); }
function getPendingSyncEvents() { try { const p = JSON.parse(localStorage.getItem(PENDING_SYNC_STORAGE_KEY) || "[]"); return Array.isArray(p) ? p : []; } catch { return []; } }
function savePendingSyncEvents(e) { localStorage.setItem(PENDING_SYNC_STORAGE_KEY, JSON.stringify(e)); }
function getDieselEntries() { try { return JSON.parse(localStorage.getItem(DIESEL_ENTRIES_KEY) || "[]"); } catch { return []; } }
function saveDieselEntries(e) { localStorage.setItem(DIESEL_ENTRIES_KEY, JSON.stringify(e)); }

function updateDbSyncStatus(customText) {
  const pending = getPendingSyncEvents().length;
  if (!SUPABASE_URL) { dbSyncStatus.textContent = "Banco nao configurado."; dbSyncStatus.className = "connection-status offline"; return; }
  if (pending === 0) { dbSyncStatus.textContent = customText || "Sincronizacao com banco em dia."; dbSyncStatus.className = "connection-status online"; return; }
  dbSyncStatus.textContent = `${pending} lancamento(s) aguardando envio ao banco.`;
  dbSyncStatus.className = "connection-status offline";
}

async function syncEventToSupabase(event) {
  const p = event.payload;
  if (event.type === "abastecimento") {
    await supabaseInsert("posto", { id: p.id, vehicle: p.vehicle, fuel_type: p.fuelType, liters: parseFloat(p.liters), hourmeter: p.hourmeterOdometer||null, work_front: p.workFront||null, work_type: p.workType||null, created_at: p.createdAt, synced_at: new Date().toISOString() });
    return;
  }
  if (event.type === "recebimento") {
    await supabaseInsert("comboio", { id: p.id, order_number: p.orderNumber, tipo_servico: p.tipoServico, vehicle: p.vehicle, fuel_type: p.fuelType||null, liters: p.liters ? parseFloat(p.liters) : null, hourmeter: p.hourmeterOdometer||null, location: p.location||null, work_type: p.workType||null, created_at: p.createdAt, synced_at: new Date().toISOString() });
    if (p.lubrication && p.tipoServico !== "abastecimento") {
      const lub = p.lubrication;
      await supabaseInsert("lubrificacao", { id: makeId(), comboio_id: p.id, order_number: p.orderNumber, vehicle: p.vehicle, location: p.location||null, actions: (lub.actions||[]).join(", "), oil_line1: lub.oilLine1||null, oil_line2: lub.oilLine2||null, oil_line3: lub.oilLine3||null, filter_line1: lub.filterLine1||null, filter_line2: lub.filterLine2||null, proxima_troca: lub.proximaTroca||null, observation: lub.observation||null, created_at: p.createdAt, synced_at: new Date().toISOString() });
    }
    return;
  }
  if (event.type === "diesel_entrada") {
    await supabaseInsert("diesel_entrada", { id: p.id, liters: parseFloat(p.liters), created_at: p.createdAt });
  }
}

async function processPendingSyncEvents() {
  if (!SUPABASE_URL || !navigator.onLine) { updateDbSyncStatus(); return; }
  let queue = getPendingSyncEvents();
  while (queue.length) {
    const event = queue[0];
    try { await syncEventToSupabase(event); queue = queue.slice(1); savePendingSyncEvents(queue); }
    catch (err) { console.error("Sync falhou:", err); break; }
  }
  updateDbSyncStatus();
}

function enqueueSyncEvent(type, payload) {
  const queue = getPendingSyncEvents();
  queue.push({ id: makeId(), type, payload, createdAt: new Date().toISOString() });
  savePendingSyncEvents(queue); updateDbSyncStatus(); processPendingSyncEvents();
}

function renderFuelOptionsSettings() {
  fuelOptionsList.innerHTML = "";
  POST_FUEL_OPTIONS.forEach((fuel) => {
    const item = document.createElement("li"); item.className = "fuel-option-item";
    item.innerHTML = `<span>${fuel}</span><span>Regra fixa</span>`; fuelOptionsList.appendChild(item);
  });
}

function fillFuelSelects() {
  if (!fuelTypeSelect || !receiptFuelTypeSelect) return;
  const selP = fuelTypeSelect.value; const selC = receiptFuelTypeSelect.value;
  fuelTypeSelect.innerHTML = "<option value=''>Selecione</option>";
  receiptFuelTypeSelect.innerHTML = "<option value=''>Selecione</option>";
  POST_FUEL_OPTIONS.forEach((f) => {
    const o1 = document.createElement("option"); o1.value = o1.textContent = f; fuelTypeSelect.appendChild(o1);
    const o2 = document.createElement("option"); o2.value = o2.textContent = f; receiptFuelTypeSelect.appendChild(o2);
  });
  if (selP && POST_FUEL_OPTIONS.includes(selP)) fuelTypeSelect.value = selP;
  if (selC && RECEIPT_FUEL_OPTIONS.includes(selC)) receiptFuelTypeSelect.value = selC;
}

function getTotalDieselEntradas() { return getDieselEntries().reduce((s, e) => s + Number(e.liters||0), 0); }
function getTotalDieselSaidas() { return getReceipts().filter(r => r.tipoServico !== "lubrificacao" && (r.fuelType||"").toLowerCase().includes("diesel")).reduce((s, r) => s + Number(r.liters||0), 0); }

function renderDieselSaldo() {
  const entradas = getTotalDieselEntradas(); const saidas = getTotalDieselSaidas(); const saldo = entradas - saidas;
  const fmt = (v) => v.toFixed(1).replace(".", ",") + " L";
  const elE = document.getElementById("diesel-entradas"); const elS = document.getElementById("diesel-saidas"); const elSal = document.getElementById("diesel-saldo");
  if (elE) elE.textContent = fmt(entradas); if (elS) elS.textContent = fmt(saidas);
  if (elSal) { elSal.textContent = fmt(saldo); elSal.style.color = saldo < 0 ? "var(--danger)" : "#127446"; }
}

function renderRecentPosto() {
  const last5 = getRecords().slice(-5).reverse(); recentPostoList.innerHTML = "";
  if (!last5.length) { recentPostoList.innerHTML = "<li class='recent-item recent-empty'><span class='recent-cell'>Nenhum abastecimento ainda.</span></li>"; return; }
  last5.forEach((r) => { const li = document.createElement("li"); li.className = "recent-item"; li.setAttribute("role","row"); li.innerHTML = `<span class="recent-cell">${escapeHtml(r.vehicle||"-")}</span><span class="recent-cell">${escapeHtml(r.fuelType||"-")}</span><span class="recent-cell">${escapeHtml(r.liters||"0")} L</span>`; recentPostoList.appendChild(li); });
}

function renderRecentComboio() {
  const last5 = getReceipts().slice(-5).reverse(); recentComboioList.innerHTML = "";
  if (!last5.length) { recentComboioList.innerHTML = "<li class='recent-item recent-item-4 recent-empty'><span class='recent-cell'>Nenhum servico ainda.</span></li>"; return; }
  last5.forEach((r) => { const li = document.createElement("li"); li.className = "recent-item recent-item-4"; li.setAttribute("role","row"); const tipo = r.tipoServico === "lubrificacao" ? "Lub" : r.tipoServico === "ambos" ? "Ambos" : "Abast"; const qty = r.tipoServico === "lubrificacao" ? "-" : `${escapeHtml(String(r.liters||"0"))} L`; li.innerHTML = `<span class="recent-cell">${escapeHtml(r.orderNumber||"-")}</span><span class="recent-cell">${escapeHtml(r.vehicle||"-")}</span><span class="recent-cell">${tipo}</span><span class="recent-cell">${qty}</span>`; recentComboioList.appendChild(li); });
}

function escapeHtml(text) { const d = document.createElement("div"); d.textContent = String(text); return d.innerHTML; }
function renderAll() { renderRecentPosto(); renderRecentComboio(); }

function updateConnectionStatus() {
  if (navigator.onLine) { connectionStatus.textContent = "Online"; connectionStatus.className = "connection-status online"; }
  else { connectionStatus.textContent = "Offline - dados salvos localmente"; connectionStatus.className = "connection-status offline"; }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const fd = new FormData(form);
  const fuelType = String(fd.get("fuelType")||"").trim();
  if (!POST_FUEL_OPTIONS.includes(fuelType)) return;
  const record = { id: makeId(), vehicle: fd.get("vehicle"), fuelType, liters: Number(fd.get("liters")).toFixed(1), hourmeterOdometer: String(fd.get("hourmeterOdometer")||"").trim(), workFront: String(fd.get("workFront")||"").trim(), workType: String(fd.get("workType")||"").trim(), source: "posto", createdAt: toIsoFromDateTimeLocal(String(fd.get("fuelDateTime")||"")) };
  const records = getRecords(); records.push(record); saveRecords(records);
  enqueueSyncEvent("abastecimento", record);
  form.reset(); fuelDateTimeInput.value = getNowLocalDateTimeInputValue(); fillFuelSelects(); renderFuelOptionsSettings(); renderAll();
});

receiptForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const fd = new FormData(receiptForm);
  const tipo = getTipoServico();
  if (tipo !== "lubrificacao") { const ft = String(fd.get("receiptFuelType")||"").trim(); if (!RECEIPT_FUEL_OPTIONS.includes(ft)) return; }
  const lubeActions = fd.getAll("lubeActions");
  if (tipo !== "abastecimento") { const reqObs = lubeActions.includes("corretiva") || lubeActions.includes("completar_nivel"); if (reqObs && !String(fd.get("lubeObservation")||"").trim()) return; }
  const orderNumber = assignNextOrderNumber();
  const fuelType = tipo !== "lubrificacao" ? String(fd.get("receiptFuelType")||"").trim() : "";
  const litersRaw = fd.get("receiptLiters");
  const liters = tipo !== "lubrificacao" && litersRaw ? Number(litersRaw).toFixed(1) : "0.0";
  const receipt = { id: makeId(), orderNumber, tipoServico: tipo, vehicle: String(fd.get("receiptVehicle")||"").trim(), fuelType, liters, hourmeterOdometer: String(fd.get("receiptHourmeter")||"").trim(), location: String(fd.get("receiptLocation")||"").trim(), workType: String(fd.get("receiptWorkType")||"").trim(), lubrication: tipo !== "abastecimento" ? { actions: lubeActions, oilLine1: String(fd.get("lubeOilType1")||"").trim(), oilLine2: String(fd.get("lubeOilType2")||"").trim(), oilLine3: String(fd.get("lubeOilType3")||"").trim(), filterLine1: String(fd.get("lubeFilterType1")||"").trim(), filterLine2: String(fd.get("lubeFilterType2")||"").trim(), proximaTroca: String(fd.get("lubeProximaTroca")||"").trim(), observation: String(fd.get("lubeObservation")||"").trim() } : null, source: "comboio", createdAt: toIsoFromDateTimeLocal(String(fd.get("receiptDateTime")||"")) };
  const receipts = getReceipts(); receipts.push(receipt); saveReceipts(receipts);
  enqueueSyncEvent("recebimento", receipt);
  receiptForm.reset(); receiptDateTimeInput.value = getNowLocalDateTimeInputValue(); atualizarSecoesPorTipo(); toggleLubeObservationField(); updateOrderPreview(); fillFuelSelects(); renderFuelOptionsSettings(); renderAll(); renderDieselSaldo();
});

const dieselEntryForm = document.getElementById("diesel-entry-form");
const dieselEntryInput = document.getElementById("diesel-entry-input");
if (dieselEntryForm) {
  dieselEntryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const liters = parseFloat(dieselEntryInput.value);
    if (!liters || liters <= 0) return;
    const entry = { id: makeId(), liters: liters.toFixed(1), createdAt: new Date().toISOString() };
    const entries = getDieselEntries(); entries.push(entry); saveDieselEntries(entries);
    enqueueSyncEvent("diesel_entrada", entry);
    dieselEntryForm.reset(); renderDieselSaldo();
  });
}

fuelSettingsForm.addEventListener("submit", (event) => { event.preventDefault(); window.alert("Acao bloqueada."); newFuelOptionInput.value = ""; });
gatePostoButton.addEventListener("click", () => enterWorkspace("posto"));
gateComboioButton.addEventListener("click", () => enterWorkspace("comboio"));
changeAreaButton.addEventListener("click", () => showGate());
receiptForm.querySelectorAll('input[name="lubeActions"]').forEach((cb) => cb.addEventListener("change", toggleLubeObservationField));
window.addEventListener("online", updateConnectionStatus);
window.addEventListener("offline", updateConnectionStatus);
window.addEventListener("online", processPendingSyncEvents);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    try { const reg = await navigator.serviceWorker.register("./sw.js?v=18", { updateViaCache: "none" }); reg.update(); }
    catch (e) { console.error("SW:", e); }
  });
}

fillFuelSelects(); renderFuelOptionsSettings(); setDefaultDateTimes(); atualizarSecoesPorTipo(); toggleLubeObservationField(); updateOrderPreview(); updateConnectionStatus(); updateDbSyncStatus(); processPendingSyncEvents(); renderAll(); renderDieselSaldo();
