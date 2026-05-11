/**
 * URL da API (sem barra no final).
 *
 * Ordem de prioridade:
 * 1) localStorage.APP_API_BASE_URL (util para teste sem alterar arquivo)
 * 2) Rede local: hostname 192.168.x / 10.x → mesma maquina porta 3000
 * 3) localhost / 127.0.0.1 → http://localhost:3000/api
 * 4) GitHub Pages / internet: edite PROD_API abaixo com HTTPS do seu backend
 */
(function () {
  try {
    var fromLs = localStorage.getItem("APP_API_BASE_URL");
    if (fromLs && String(fromLs).trim()) {
      window.APP_API_BASE_URL = String(fromLs).trim().replace(/\/$/, "");
      return;
    }
  } catch (e) {}

  var h = typeof location !== "undefined" ? location.hostname || "" : "";

  if (h === "localhost" || h === "127.0.0.1") {
    window.APP_API_BASE_URL = "http://localhost:3000/api";
    return;
  }

  if (/^192\.168\./.test(h) || /^10\./.test(h)) {
    window.APP_API_BASE_URL = ("http://" + h + ":3000/api").replace(/\/$/, "");
    return;
  }

  // Producao (ex.: GitHub Pages): coloque a URL HTTPS da API publicada.
  var PROD_API = "";
  window.APP_API_BASE_URL = String(PROD_API).replace(/\/$/, "");
})();
