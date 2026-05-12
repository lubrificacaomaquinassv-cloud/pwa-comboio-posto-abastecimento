/**
 * URL da API (sem barra no final).
 *
 * Ordem:
 * 1) localStorage.APP_API_BASE_URL (forca manual; apague a chave se quiser voltar ao PROD_API)
 * 2) localhost / 127.0.0.1 -> API neste PC, porta 3000
 * 3) Wi-Fi (192.168.* / 10.*) -> mesmo IP, porta 3000
 * 4) Abrir index.html como arquivo (file://) -> assume API neste PC (127.0.0.1:3000)
 * 5) Internet (ex.: GitHub Pages): PROD_API abaixo (Apps Script termina em /exec)
 */
(function () {
  try {
    var fromLs = localStorage.getItem("APP_API_BASE_URL");
    if (fromLs && String(fromLs).trim()) {
      window.APP_API_BASE_URL = String(fromLs).trim().replace(/\/$/, "");
      return;
    }
  } catch (e) {
    /* localStorage indisponivel (ex.: modo privado restrito) */
  }

  var loc = typeof location !== "undefined" ? location : { hostname: "", protocol: "" };
  var h = loc.hostname || "";

  if (h === "localhost" || h === "127.0.0.1") {
    window.APP_API_BASE_URL = "http://localhost:3000/api";
    return;
  }

  if (/^192\.168\./.test(h) || /^10\./.test(h)) {
    window.APP_API_BASE_URL = ("http://" + h + ":3000/api").replace(/\/$/, "");
    return;
  }

  if (loc.protocol === "file:") {
    window.APP_API_BASE_URL = "http://127.0.0.1:3000/api";
    return;
  }

  var PROD_API =
    "https://script.google.com/macros/s/AKfycbw7mKvUDmWM6-KmHCNRH5Yl0Jtcq6mkMuFGzJmEXfWAbbYLVFxuB-z6yDnWne7rLnZO/exec";
  PROD_API = String(PROD_API || "")
    .trim()
    .replace(/\/$/, "");
  window.APP_API_BASE_URL = PROD_API;
})();

/**
 * Se criou SHARED_SECRET no Apps Script, preencha com o MESMO texto (senao sync devolve nao autorizado).
 * Deixe "" se nao usar segredo no script (nao recomendado em producao).
 */
window.SHEETS_SYNC_SECRET = "";
