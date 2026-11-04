(function () {
  if (window.AGENCY_API_BASE) return;
  var host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    window.AGENCY_API_BASE = "http://127.0.0.1:9815/api/v1";
  } else {
    window.AGENCY_API_BASE = window.location.origin + "/api/v1";
  }
})();
