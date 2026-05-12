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
const API_BASE_URL = (window.APP_API_BASE_URL || "").trim().replace(/\/$/, "");

function syncPostUrl() {
  if (!API_BASE_URL) return "";
  if (API_BASE_URL.indexOf("script.google.com") !== -1) return API_BASE_URL;
  return `${API_BASE_URL}/lancamentos`;
}

const form = document.getElementById("fuel-form");
const receiptForm = document.getElementById("receipt-form");
const postoSection = document.getElementById("posto-section");
const comboioSection = document.getElementById("comboio-section");
const recentPostoSection = document.getElementById("recent-posto-section");
const recentComboioSection = document.getElementById("recent-comboio-section");
const modePostoButton = document.getElementById("mode-posto");
const modeComboioButton = document.getElementById("mode-comboio");
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

function setActiveMode(mode) {
  const isPosto = mode === "posto";
  postoSection.classList.toggle("hidden", !isPosto);
  comboioSection.classList.toggle("hidden", isPosto);
  recentPostoSection.classList.toggle("hidden", !isPosto);
  recentComboioSection.classList.toggle("hidden", isPosto);
  modePostoButton.classList.toggle("active", isPosto);
  modeComboioButton.classList.toggle("active", !isPosto);
  modePostoButton.setAttribute("aria-selected", String(isPosto));
  modeComboioButton.setAttribute("aria-selected", String(!isPosto));
  if (!isPosto) {
    updateOrderPreview();
  }
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
  const url = syncPostUrl();
  if (!url) {
    updateDbSyncStatus();
    return;
  }
  let queue = getPendingSyncEvents();
  while (queue.length) {
    const event = queue[0];
    try {
      const bodyObj = { ...event };
      const sec =
        typeof window.SHEETS_SYNC_SECRET === "string" ? window.SHEETS_SYNC_SECRET.trim() : "";
      if (sec) bodyObj.secret = sec;
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyObj),
      });
      const text = await response.text();
      let data = null;
      try {
        data = JSON.parse(text);
      } catch {
        /* ignore */
      }
      if (!response.ok) break;
      if (data && data.ok === false) break;
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
  queue.push({
    id: makeId(),
    type,
    payload,
    createdAt: new Date().toISOString(),
  });
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
  if (!fuelTypeSelect || !receiptFuelTypeSelect) return;
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

modePostoButton.addEventListener("click", () => setActiveMode("posto"));
modeComboioButton.addEventListener("click", () => setActiveMode("comboio"));
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
      await navigator.serviceWorker.register(SW_URL);
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
setActiveMode("posto");
updateConnectionStatus();
updateDbSyncStatus();
processPendingSyncEvents();
renderAll();
