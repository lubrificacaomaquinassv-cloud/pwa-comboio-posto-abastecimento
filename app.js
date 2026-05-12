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

/* =========================
   CORREÇÃO DO GOOGLE SHEETS
========================= */
function syncPostUrl() {
  if (!API_BASE_URL) return "";

  // GOOGLE APPS SCRIPT
  if (API_BASE_URL.includes("script.google.com")) {
    return API_BASE_URL;
  }

  // NODE LOCAL
  return `${API_BASE_URL}/lancamentos`;
}

const form = document.getElementById("fuel-form");
const receiptForm = document.getElementById("receipt-form");

function makeId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
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

  if (Number.isNaN(date.getTime())) {
    return new Date().toISOString();
  }

  return date.toISOString();
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

async function processPendingSyncEvents() {
  if (!API_BASE_URL || !navigator.onLine) {
    return;
  }

  let queue = getPendingSyncEvents();

  while (queue.length) {
    const event = queue[0];

    try {
      const response = await fetch(syncPostUrl(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(event),
      });

      const text = await response.text();

      let data = null;

      try {
        data = JSON.parse(text);
      } catch {
        break;
      }

      if (!response.ok || (data && data.ok === false)) {
        console.error("ERRO GOOGLE SHEETS:", data);
        break;
      }

      queue = queue.slice(1);

      savePendingSyncEvents(queue);

    } catch (err) {
      console.error("FALHA ENVIO:", err);
      break;
    }
  }
}

function enqueueSyncEvent(type, payload) {
  const queue = getPendingSyncEvents();

  const ev = {
    id: makeId(),
    type,
    payload,
    createdAt: new Date().toISOString(),
  };

  queue.push(ev);

  savePendingSyncEvents(queue);

  processPendingSyncEvents();
}

function assignNextOrderNumber() {
  const n = Number(localStorage.getItem(ORDER_SEQ_KEY) || "0") + 1;

  localStorage.setItem(ORDER_SEQ_KEY, String(n));

  return `COM-${String(n).padStart(5, "0")}`;
}

/* =========================
   POSTO
========================= */

form.addEventListener("submit", (event) => {

  event.preventDefault();

  const formData = new FormData(form);

  const fuelType = String(formData.get("fuelType") || "").trim();

  const record = {
    id: makeId(),
    vehicle: formData.get("vehicle"),
    fuelType,
    liters: Number(formData.get("liters")).toFixed(1),
    hourmeterOdometer: String(formData.get("hourmeterOdometer") || "").trim(),
    workFront: String(formData.get("workFront") || "").trim(),
    workType: String(formData.get("workType") || "").trim(),
    source: "posto",
    createdAt: toIsoFromDateTimeLocal(
      String(formData.get("fuelDateTime") || "")
    ),
  };

  const records = getRecords();

  records.push(record);

  saveRecords(records);

  enqueueSyncEvent("abastecimento", record);

  form.reset();

  document.getElementById("fuelDateTime").value =
    getNowLocalDateTimeInputValue();

  alert("Abastecimento salvo.");
});

/* =========================
   COMBOIO
========================= */

receiptForm.addEventListener("submit", (event) => {

  event.preventDefault();

  const formData = new FormData(receiptForm);

  const orderNumber = assignNextOrderNumber();

  const receipt = {
    id: makeId(),
    orderNumber,

    vehicle: String(
      formData.get("receiptVehicle") || ""
    ).trim(),

    fuelType: String(
      formData.get("receiptFuelType") || ""
    ).trim(),

    liters: Number(
      formData.get("receiptLiters")
    ).toFixed(1),

    location: String(
      formData.get("receiptLocation") || ""
    ).trim(),

    workType: String(
      formData.get("receiptWorkType") || ""
    ).trim(),

    lubrication: {
      actions: formData.getAll("lubeActions"),

      oilLine1: String(
        formData.get("lubeOilType1") || ""
      ).trim(),

      oilLine2: String(
        formData.get("lubeOilType2") || ""
      ).trim(),

      filterLine1: String(
        formData.get("lubeFilterType1") || ""
      ).trim(),

      filterLine2: String(
        formData.get("lubeFilterType2") || ""
      ).trim(),

      observation: String(
        formData.get("lubeObservation") || ""
      ).trim(),
    },

    source: "comboio",

    createdAt: toIsoFromDateTimeLocal(
      String(formData.get("receiptDateTime") || "")
    ),
  };

  const receipts = getReceipts();

  receipts.push(receipt);

  saveReceipts(receipts);

  enqueueSyncEvent("recebimento", receipt);

  receiptForm.reset();

  document.getElementById("receiptDateTime").value =
    getNowLocalDateTimeInputValue();

  alert("Recebimento salvo.");
});

/* =========================
   INICIALIZAÇÃO
========================= */

window.addEventListener("online", processPendingSyncEvents);

document.getElementById("fuelDateTime").value =
  getNowLocalDateTimeInputValue();

document.getElementById("receiptDateTime").value =
  getNowLocalDateTimeInputValue();

processPendingSyncEvents();
