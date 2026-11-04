(function () {
  const API_BASE = window.AGENCY_API_BASE || "http://localhost:8000/api/v1";
  const btn = document.getElementById("generate-pitches");
  const list = document.getElementById("prospect-list");
  const secretEl = document.getElementById("admin-secret");
  const out = document.getElementById("pitch-results");
  const err = document.getElementById("pitch-error");

  function normalizeSecret(raw) {
    let s = (raw || "").trim();
    if (/^ADMIN_SECRET=/i.test(s)) s = s.replace(/^ADMIN_SECRET=/i, "").trim();
    if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
      s = s.slice(1, -1).trim();
    }
    return s;
  }

  function parseProspects(raw) {
    return raw
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((line) => {
        const [domain, org] = line.split(",").map((s) => s.trim());
        return { domain: domain || "", organization: org || domain };
      })
      .filter((p) => p.domain);
  }

  btn?.addEventListener("click", async () => {
    err.classList.add("hidden");
    out.innerHTML = "";
    const secret = normalizeSecret(secretEl.value);
    if (!secret) {
      err.textContent = "Admin secret required.";
      err.classList.remove("hidden");
      return;
    }
    const prospects = parseProspects(list.value);
    if (!prospects.length) {
      err.textContent = "Add at least one prospect line.";
      err.classList.remove("hidden");
      return;
    }
    btn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/admin/pitch/generate?secret=${encodeURIComponent(secret)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prospects }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Generation failed");
      out.innerHTML = data.items
        .map(
          (item) => `
        <article class="bg-[#111827] border border-slate-800 rounded-xl p-5">
          <h3 class="font-semibold">${item.organization} <span class="text-slate-500 text-sm">(${item.domain})</span></h3>
          <p class="text-xs text-slate-500 mt-2">Pitch link</p>
          <a class="text-cyan-400 text-sm break-all" href="${item.pitch_link}" target="_blank" rel="noopener">${item.pitch_link}</a>
          <p class="text-xs text-slate-500 mt-4">Email template</p>
          <pre class="text-xs mt-2 bg-[#0B0F19] p-3 rounded border border-slate-700 whitespace-pre-wrap">${item.email_template.replace(/</g, "&lt;")}</pre>
        </article>`
        )
        .join("");
    } catch (e) {
      err.textContent =
        e.message === "Failed to fetch"
          ? "Cannot reach API — keep ./start-dev.sh running on port 9815."
          : e.message;
      err.classList.remove("hidden");
    } finally {
      btn.disabled = false;
    }
  });
})();
