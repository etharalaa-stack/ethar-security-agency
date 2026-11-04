(function () {
  const API_BASE = window.AGENCY_API_BASE || "http://localhost:8000/api/v1";

  const form = document.getElementById("quick-scan-form");
  const input = document.getElementById("quick-scan-target");
  const orgInput = document.getElementById("quick-scan-org");
  const panel = document.getElementById("quick-scan-results");
  const scoreEl = document.getElementById("scan-score");
  const greetEl = document.getElementById("scan-greeting");
  const alertsEl = document.getElementById("scan-alerts");
  const recEl = document.getElementById("scan-recommended");
  const errEl = document.getElementById("quick-scan-error");
  const btn = document.getElementById("quick-scan-btn");

  function applyRecommendedParts(partIds) {
    if (!window.__etharSelectParts || !partIds?.length) return;
    window.__etharSelectParts(partIds);
  }

  async function runScan(target, organization) {
    errEl.classList.add("hidden");
    panel.classList.add("hidden");
    btn.disabled = true;
    btn.textContent = "Scanning…";
    try {
      const res = await fetch(`${API_BASE}/public/quick-scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, organization: organization || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Scan failed");
      scoreEl.textContent = `${data.posture_score}/100`;
      scoreEl.className =
        data.posture_score >= 85
          ? "text-4xl font-bold text-emerald-400"
          : data.posture_score >= 65
            ? "text-4xl font-bold text-cyan-400"
            : "text-4xl font-bold text-red-400";
      greetEl.textContent = data.personalized_greeting;
      alertsEl.innerHTML = (data.alerts || [])
        .map(
          (a) =>
            `<div class="border border-slate-700 rounded-lg p-3 mb-2">
              <p class="text-xs text-red-400 font-semibold">${a.severity} · ${a.component}</p>
              <p class="text-sm mt-1">${a.title}</p>
              <pre class="text-xs mt-2 text-slate-500 bg-[#0B0F19] p-2 rounded overflow-x-auto">${a.remediation_preview.replace(/</g, "&lt;")}</pre>
            </div>`
        )
        .join("");
      recEl.innerHTML = (data.recommended_part_details || [])
        .map(
          (p) =>
            `<span class="inline-block mr-2 mb-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs">${p.title} ($${p.price_usd})</span>`
        )
        .join("");
      panel.classList.remove("hidden");
      applyRecommendedParts(data.recommended_parts);
      const targetField = document.getElementById("target-asset");
      const orgField = document.getElementById("organization");
      if (targetField && !targetField.value) targetField.value = data.target;
      if (orgField && organization && !orgField.value) orgField.value = organization;
    } catch (e) {
      errEl.textContent = e.message || "Scan unavailable";
      errEl.classList.remove("hidden");
    } finally {
      btn.disabled = false;
      btn.textContent = "Run Free Live Scan";
    }
  }

  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    runScan(input.value.trim(), orgInput?.value?.trim());
  });

  const params = new URLSearchParams(window.location.search);
  const pitchTarget = params.get("target");
  const pitchOrg = params.get("org");
  if (pitchTarget) {
    if (input) input.value = pitchTarget;
    if (orgInput && pitchOrg) orgInput.value = pitchOrg;
    const banner = document.getElementById("pitch-banner");
    if (banner && pitchOrg) {
      banner.classList.remove("hidden");
      banner.textContent = `Personalized engagement for ${pitchOrg} — live perimeter snapshot loading…`;
    }
    runScan(pitchTarget, pitchOrg || undefined);
  }
})();
