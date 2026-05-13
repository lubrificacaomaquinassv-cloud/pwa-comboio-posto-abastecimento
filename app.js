const STORAGE_KEY = "comboio-fuel-records";
const RECEIPTS_STORAGE_KEY = "comboio-fuel-receipts";
const PENDING_SYNC_STORAGE_KEY = "comboio-pending-sync-events";
const ORDER_SEQ_KEY = "comboio-order-seq";
const POST_FUEL_OPTIONS = [
  "Gasolina Comum",
  "Etanol Comum",
  "Diesel S-10",
  "Diesel S-500 Aditivado",
  "Diesel S-500 Comum",
];
const RECEIPT_FUEL_OPTIONS = [...POST_FUEL_OPTIONS];
const API_BASE_URL = (window.APP_API_BASE_URL || "").replace(/\/$/, "");

/** URL POST de sync: Node usa /lancamentos; Google Apps Script usa so o URL /exec. */
function syncPostUrl() {
  if (!API_BASE_URL) return "";
  if (API_BASE_URL.indexOf("script.google.com") !== -1) return API_BASE_URL;
  return `${API_BASE_URL}/lancamentos`;
}

const form = document.getElementById("fuel-form");
const receiptForm = document.getElementById("receipt-form");
const workspacePosto = document.getElementById("workspace-posto");
const workspaceComboio = document.getElementById("workspace-comboio");
const trailingConfig = document.getElementById("trailing-config");
const trailingInforme = document.getElementById("trailing-informe");
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

function attachTrailingBlocks(mode) {
  if (mode === "posto") {
    workspacePosto.appendChild(trailingConfig);
    workspacePosto.appendChild(trailingInforme);
  } else {
    workspacePosto.appendChild(trailingConfig);
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
  if (!isPosto) {
    updateOrderPreview();
  }
  areaLabel.textContent = isPosto
    ? "Fluxo do posto (escolhido no inicio). Nada do comboio nesta tela."
    : "Fluxo do comboio (escolhido no inicio). Nada do posto nesta tela.";
  if (appWorkflowHeading && appWorkflowSub) {
    appWorkflowHeading.textContent = isPosto ? "Posto de abastecimento" : "Comboio";
    appWorkflowSub.textContent = isPosto
      ? "Voce escolheu posto no inicio. Abaixo so entra lancamento do posto fixo."
      : "Voce escolheu comboio no inicio. Abaixo so entra recebimento e servico no campo.";
  }
  document.title = isPosto ? "Posto | Abastecimento frota" : "Comboio | Abastecimento frota";
  fillFuelSelects();
  renderFuelOptionsSettings();
  window.scrollTo(0, 0);
}

function getNowLocalDateTimeInputValue() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

function toIsoFromDateTimeLocal(value) {
  if (!value) return new Date().toISOString();
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return new Date().toISOString();
  return date.toISOString();
}

function setDefaultDateTimes() {
  if (!fuelDateTimeInput.value) {
    fuelDateTimeInput.value = getNowLocalDateTimeInputValue();
  }
  if (!receiptDateTimeInput.value) {
    receiptDateTimeInput.value = getNowLocalDateTimeInputValue();
  }
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
  const actions = [...receiptForm.querySelectorAll('input[name="lubeActions"]:checked')].map(
    (node) => node.value
  );
  const requiresObservation =
    actions.includes("corretiva") || actions.includes("completar_nivel");
  lubeObservationWrap.classList.toggle("hidden", !requiresObservation);
  lubeObservationInput.required = requiresObservation;
  if (!requiresObservation) lubeObservationInput.value = "";
}

function makeId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

function getRecords() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveRecords(records) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

function getReceipts() {
  const raw = localStorage.getItem(RECEIPTS_STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveReceipts(receipts) {
  localStorage.setItem(RECEIPTS_STORAGE_KEY, JSON.stringify(receipts));
}

function getPendingSyncEvents() {
  const raw = localStorage.getItem(PENDING_SYNC_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function savePendingSyncEvents(events) {
  localStorage.setItem(PENDING_SYNC_STORAGE_KEY, JSON.stringify(events));
}

function updateDbSyncStatus(customText) {
  const pending = getPendingSyncEvents().length;
  if (!API_BASE_URL) {
    dbSyncStatus.textContent = "Banco nao configurado (defina window.APP_API_BASE_URL).";
    dbSyncStatus.className = "connection-status offline";
    return;
  }
  if (pending === 0) {
    dbSyncStatus.textContent = customText || "Sincronizacao com banco em dia.";
    dbSyncStatus.className = "connection-status online";
    return;
  }
  dbSyncStatus.textContent = `${pending} lancamento(s) aguardando envio ao banco.`;
  dbSyncStatus.className = "connection-status offline";
}

async function processPendingSyncEvents() {
  if (!API_BASE_URL || !navigator.onLine) {
    updateDbSyncStatus();
    return;
  }
  let queue = getPendingSyncEvents();
  while (queue.length) {
    const event = queue[0];
    try {
      const url = syncPostUrl() + "?payload=" + encodeURIComponent(JSON.stringify(event));
      const response = await fetch(url);
      const text = await response.text();
      let data = null;
      try {
        data = JSON.parse(text);
      } catch {
        break;
      }
      if (!data || data.ok === false) {
        console.error("Sync recusado:", data && data.error);
        break;
      }
      queue = queue.slice(1);
      savePendingSyncEvents(queue);
    } catch {
      break;
    }
  }
  updateDbSyncStatus();
}

function enqueueSyncEvent(type, payload) {
  const queue = getPendingSyncEvents();
  const ev = {
    id: makeId(),
    type,
    payload,
    createdAt: new Date().toISOString(),
  };
  const shSecret = typeof window !== "undefined" && window.SHEETS_SYNC_SECRET;
  if (shSecret && String(shSecret).trim()) {
    ev.secret = String(shSecret).trim();
  }
  queue.push(ev);
  savePendingSyncEvents(queue);
  updateDbSyncStatus();
  processPendingSyncEvents();
}

function getUniqueFuelOptions() {
  const records = getRecords();
  const receipts = getReceipts();
  const dynamicOptions = records.map((record) => record.fuelType);
  const dynamicReceiptOptions = receipts.map((receipt) => receipt.fuelType);
  return [
    ...new Set([
      ...POST_FUEL_OPTIONS,
      ...RECEIPT_FUEL_OPTIONS,
      ...dynamicOptions,
      ...dynamicReceiptOptions,
    ]),
  ].sort((a, b) => a.localeCompare(b, "pt-BR"));
}

function renderFuelOptionsSettings() {
  const options = getUniqueFuelOptions();
  fuelOptionsList.innerHTML = "";

  if (!options.length) {
    fuelOptionsList.innerHTML =
      "<li class='fuel-option-item'><span>Nenhum combustivel cadastrado.</span></li>";
    return;
  }

  options.forEach((fuel) => {
    const item = document.createElement("li");
    item.className = "fuel-option-item";
    item.innerHTML = `
      <span>${fuel}</span>
      <span>Regra fixa</span>
    `;

    fuelOptionsList.appendChild(item);
  });
}

function fillFuelSelects() {
  if (!fuelTypeSelect || !receiptFuelTypeSelect) {
    console.warn("fillFuelSelects: select de combustivel nao encontrado no DOM.");
    return;
  }
  const selectedFuelType = fuelTypeSelect.value;
  const selectedReceiptFuelType = receiptFuelTypeSelect.value;

  fuelTypeSelect.innerHTML = "<option value=''>Selecione</option>";
  POST_FUEL_OPTIONS.forEach((fuelType) => {
    const option = document.createElement("option");
    option.value = fuelType;
    option.textContent = fuelType;
    fuelTypeSelect.appendChild(option);
  });

  receiptFuelTypeSelect.innerHTML = "<option value=''>Selecione</option>";
  RECEIPT_FUEL_OPTIONS.forEach((fuelType) => {
    const option = document.createElement("option");
    option.value = fuelType;
    option.textContent = fuelType;
    receiptFuelTypeSelect.appendChild(option);
  });

  if (selectedFuelType && POST_FUEL_OPTIONS.includes(selectedFuelType)) {
    fuelTypeSelect.value = selectedFuelType;
  }
  if (selectedReceiptFuelType && RECEIPT_FUEL_OPTIONS.includes(selectedReceiptFuelType)) {
    receiptFuelTypeSelect.value = selectedReceiptFuelType;
  }
}

function renderRecentPosto() {
  const postoRecords = getRecords().filter((r) => r.source === "posto" || !r.source);
  recentPostoList.innerHTML = "";
  const last5 = postoRecords.slice(-5).reverse();
  if (!last5.length) {
    recentPostoList.innerHTML =
      "<li class='recent-item recent-empty'><span class='recent-cell'>Nenhum abastecimento ainda.</span></li>";
    return;
  }
  last5.forEach((record) => {
    const li = document.createElement("li");
    li.className = "recent-item";
    li.setAttribute("role", "row");
    li.innerHTML = `
      <span class="recent-cell">${escapeHtml(String(record.vehicle || "-"))}</span>
      <span class="recent-cell">${escapeHtml(String(record.fuelType || "-"))}</span>
      <span class="recent-cell">${escapeHtml(String(record.liters || "0"))} L</span>
    `;
    recentPostoList.appendChild(li);
  });
}

function renderRecentComboio() {
  const receipts = getReceipts();
  recentComboioList.innerHTML = "";
  const last5 = receipts.slice(-5).reverse();
  if (!last5.length) {
    recentComboioList.innerHTML =
      "<li class='recent-item recent-item-4 recent-empty'><span class='recent-cell'>Nenhum servico ainda.</span></li>";
    return;
  }
  last5.forEach((receipt) => {
    const li = document.createElement("li");
    li.className = "recent-item recent-item-4";
    li.setAttribute("role", "row");
    const ord = escapeHtml(String(receipt.orderNumber || "-"));
    const veh = escapeHtml(String(receipt.vehicle || "-"));
    const fuel = escapeHtml(String(receipt.fuelType || "-"));
    const qty = escapeHtml(String(receipt.liters || "0"));
    li.innerHTML = `
      <span class="recent-cell">${ord}</span>
      <span class="recent-cell">${veh}</span>
      <span class="recent-cell">${fuel}</span>
      <span class="recent-cell">${qty} L</span>
    `;
    recentComboioList.appendChild(li);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderAll() {
  renderRecentPosto();
  renderRecentComboio();
}

function updateConnectionStatus() {
  if (navigator.onLine) {
    connectionStatus.textContent = "Online";
    connectionStatus.className = "connection-status online";
  } else {
    connectionStatus.textContent = "Offline - os dados continuam salvos localmente";
    connectionStatus.className = "connection-status offline";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const fuelType = String(formData.get("fuelType") || "").trim();
  if (!POST_FUEL_OPTIONS.includes(fuelType)) return;

  const record = {
    id: makeId(),
    vehicle: formData.get("vehicle"),
    fuelType,
    liters: Number(formData.get("liters")).toFixed(1),
    hourmeterOdometer: String(formData.get("hourmeterOdometer") || "").trim(),
    workFront: String(formData.get("workFront") || "").trim(),
    workType: String(formData.get("workType") || "").trim(),
    source: "posto",
    createdAt: toIsoFromDateTimeLocal(String(formData.get("fuelDateTime") || "")),
  };

  const records = getRecords();
  records.push(record);
  saveRecords(records);
  enqueueSyncEvent("abastecimento", record);
  form.reset();
  fuelDateTimeInput.value = getNowLocalDateTimeInputValue();
  fillFuelSelects();
  renderFuelOptionsSettings();
  renderAll();
});

receiptForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(receiptForm);
  const fuelType = String(formData.get("receiptFuelType") || "").trim();
  if (!RECEIPT_FUEL_OPTIONS.includes(fuelType)) return;
  const lubeActions = formData.getAll("lubeActions");
  const requiresObservation =
    lubeActions.includes("corretiva") || lubeActions.includes("completar_nivel");
  const lubeObservation = String(formData.get("lubeObservation") || "").trim();
  if (requiresObservation && !lubeObservation) return;

  const oilLine1 = String(formData.get("lubeOilType1") || "").trim();
  const oilLine2 = String(formData.get("lubeOilType2") || "").trim();
  const filterLine1 = String(formData.get("lubeFilterType1") || "").trim();
  const filterLine2 = String(formData.get("lubeFilterType2") || "").trim();

  const orderNumber = assignNextOrderNumber();
  const vehicle = String(formData.get("receiptVehicle") || "").trim();

  const receipt = {
    id: makeId(),
    orderNumber,
    vehicle,
    fuelType,
    liters: Number(formData.get("receiptLiters")).toFixed(1),
    location: String(formData.get("receiptLocation") || "").trim(),
    workType: String(formData.get("receiptWorkType") || "").trim(),
    lubrication: {
      actions: lubeActions,
      oilLine1,
      oilLine2,
      filterLine1,
      filterLine2,
      observation: lubeObservation,
    },
    source: "comboio",
    createdAt: toIsoFromDateTimeLocal(String(formData.get("receiptDateTime") || "")),
  };

  const receipts = getReceipts();
  receipts.push(receipt);
  saveReceipts(receipts);
  enqueueSyncEvent("recebimento", receipt);
  receiptForm.reset();
  receiptDateTimeInput.value = getNowLocalDateTimeInputValue();
  toggleLubeObservationField();
  updateOrderPreview();
  fillFuelSelects();
  renderFuelOptionsSettings();
  renderAll();
});

fuelSettingsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  window.alert("Acao bloqueada: configuracoes so podem ser conciliadas pelo responsavel.");
  newFuelOptionInput.value = "";
});

gatePostoButton.addEventListener("click", () => enterWorkspace("posto"));
gateComboioButton.addEventListener("click", () => enterWorkspace("comboio"));
changeAreaButton.addEventListener("click", () => showGate());
receiptForm.querySelectorAll('input[name="lubeActions"]').forEach((checkbox) => {
  checkbox.addEventListener("change", toggleLubeObservationField);
});
window.addEventListener("online", updateConnectionStatus);
window.addEventListener("offline", updateConnectionStatus);
window.addEventListener("online", processPendingSyncEvents);

const SW_URL = "./sw.js?v=15";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    try {
      const reg = await navigator.serviceWorker.register(SW_URL, {
        updateViaCache: "none",
      });
      reg.update();
    } catch (error) {
      console.error("Falha ao registrar service worker:", error);
    }
  });
}

fillFuelSelects();
renderFuelOptionsSettings();
setDefaultDateTimes();
toggleLubeObservationField();
updateOrderPreview();
updateConnectionStatus();
updateDbSyncStatus();
processPendingSyncEvents();
renderAll();