(function () {
  const API_BASE = window.AGENCY_API_BASE || "http://localhost:8000/api/v1";

  const PARTS_FALLBACK = [
    { id: "part_1", title: "Web & API Perimeter Audit", price_usd: 100, summary: "SSL/TLS, HTTP headers, DNS/SPF/DMARC." },
    { id: "part_2", title: "Container & Repository SecOps Review", price_usd: 120, summary: "Dockerfile, compose, secrets, dependencies." },
    { id: "part_3", title: "Cloudflare WAF & Edge Shielding", price_usd: 80, summary: "Transform rules, rate limits, edge defense." },
    { id: "part_4", title: "Linux VPS & Kernel Hardening", price_usd: 150, summary: "SSH, UFW, Docker daemon, sysctl." },
    { id: "part_5", title: "CI/CD Pipeline & Data Access Review", price_usd: 90, summary: "Access control, isolation, backups." },
  ];

  const MILESTONE_MIN = 150;
  const selected = new Set(["part_1"]);
  let paymentMethod = "usdt_bep20";
  let paymentPlan = "full";
  let catalog = PARTS_FALLBACK;

  const modal = document.getElementById("order-modal");
  const sampleModal = document.getElementById("sample-modal");
  const partPreviewModal = document.getElementById("part-preview-modal");
  const partPreviewBody = document.getElementById("part-preview-body");
  const form = document.getElementById("order-form");
  const partsGrid = document.getElementById("parts-grid");
  const modalParts = document.getElementById("modal-parts-summary");
  const totalEl = document.getElementById("order-total");
  const dueNowEl = document.getElementById("due-now");
  const planFull = document.getElementById("plan-full");
  const planMilestones = document.getElementById("plan-milestones");
  const milestoneInfo = document.getElementById("milestone-info");
  const submitBtn = document.getElementById("submit-order");
  const formError = document.getElementById("form-error");

  function openModal(el) {
    el?.classList.remove("hidden");
    el?.classList.add("flex");
    document.body.classList.add("overflow-hidden");
    renderTotals();
  }

  function closeModal(el) {
    el?.classList.add("hidden");
    el?.classList.remove("flex");
    document.body.classList.remove("overflow-hidden");
  }

  function partById(id) {
    return catalog.find((p) => p.id === id) || PARTS_FALLBACK.find((p) => p.id === id);
  }

  function computeTotal() {
    return [...selected].reduce((sum, id) => sum + (partById(id)?.price_usd || 0), 0);
  }

  function dueNowAmount(total) {
    if (paymentPlan === "full") return total;
    return Math.round(total * 0.4 * 100) / 100;
  }

  function renderPartsGrid() {
    if (!partsGrid) return;
    partsGrid.innerHTML = catalog
      .map((p) => {
        const on = selected.has(p.id);
        const badge = p.badge
          ? `<span class="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300">${p.badge}</span>`
          : "";
        const deliverables = (p.deliverables || [])
          .map((d) => `<li class="text-slate-400">${d}</li>`)
          .join("");
        const eta = p.eta_hours ? `<p class="text-xs text-slate-500 mt-2">Est. desk time: ~${p.eta_hours}h</p>` : "";
        return `
        <div class="bg-[#111827] border ${on ? "border-emerald-500 ring-1 ring-emerald-500/40" : "border-slate-800"} rounded-xl p-5 hover:border-cyan-500/40 transition">
          <div class="flex gap-3 items-start">
            <input type="checkbox" data-part-id="${p.id}" class="mt-1" ${on ? "checked" : ""} />
            <div class="flex-1">
              <div class="flex flex-wrap gap-2 items-center">${badge}<p class="font-semibold">${p.title}</p></div>
              <p class="text-emerald-400 font-bold mt-1">$${p.price_usd}</p>
              <p class="text-slate-400 text-sm mt-2">${p.summary}</p>
              ${eta}
              <ul class="text-xs mt-3 list-disc pl-4 space-y-1">${deliverables}</ul>
              <button type="button" data-preview-part="${p.id}" class="mt-3 text-xs text-cyan-400 hover:text-cyan-300">Quick preview sample →</button>
            </div>
          </div>
        </div>`;
      })
      .join("");

    partsGrid.querySelectorAll("[data-preview-part]").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        const p = partById(btn.dataset.previewPart);
        if (!p || !partPreviewBody) return;
        partPreviewBody.innerHTML = `
          <h3 class="text-lg font-semibold">${p.title}</h3>
          <p class="text-emerald-400 font-bold mt-1">$${p.price_usd}</p>
          <p class="text-sm text-slate-400 mt-2">${p.summary}</p>
          <h4 class="text-sm font-semibold mt-4 text-cyan-400">Deliverables</h4>
          <ul class="list-disc pl-5 text-sm text-slate-300 mt-2">${(p.deliverables || []).map((d) => `<li>${d}</li>`).join("")}</ul>
          <h4 class="text-sm font-semibold mt-4 text-cyan-400">Output sample</h4>
          <pre class="mt-2 text-xs bg-[#0B0F19] p-3 rounded border border-slate-700 overflow-x-auto">${(p.preview_sample || "").replace(/</g, "&lt;")}</pre>`;
        openModal(partPreviewModal);
      });
    });

    partsGrid.querySelectorAll("[data-part-id]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = cb.dataset.partId;
        if (cb.checked) selected.add(id);
        else {
          if (selected.size <= 1) {
            cb.checked = true;
            return;
          }
          selected.delete(id);
        }
        renderPartsGrid();
        renderTotals();
      });
    });
  }

  function renderTotals() {
    const total = computeTotal();
    if (totalEl) totalEl.textContent = `$${total.toFixed(2)}`;
    if (dueNowEl) dueNowEl.textContent = `$${dueNowAmount(total).toFixed(2)}`;
    if (modalParts) {
      modalParts.innerHTML = [...selected]
        .map((id) => {
          const p = partById(id);
          return `<li class="flex justify-between text-sm py-1"><span>${p.title}</span><span>$${p.price_usd}</span></li>`;
        })
        .join("");
    }
    const milestoneOk = total > MILESTONE_MIN;
    if (planMilestones) {
      planMilestones.disabled = !milestoneOk;
      planMilestones.classList.toggle("opacity-40", !milestoneOk);
    }
    if (milestoneInfo) {
      milestoneInfo.textContent = milestoneOk
        ? "Milestone 1 (40%) due now · Milestone 2 (40%) before remediation · Milestone 3 (20%) before PDF release."
        : `Milestone plan available for orders over $${MILESTONE_MIN}.`;
    }
    if (!milestoneOk && paymentPlan === "milestones") {
      paymentPlan = "full";
      planFull.checked = true;
    }
  }

  document.querySelectorAll("[data-open-order]").forEach((btn) => {
    btn.addEventListener("click", () => openModal(modal));
  });

  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      closeModal(modal);
      closeModal(sampleModal);
      closeModal(partPreviewModal);
    });
  });

  document.querySelectorAll("[data-open-sample]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      openModal(sampleModal);
      const body = document.getElementById("sample-sections");
      if (!body || body.dataset.loaded) return;
      try {
        const res = await fetch(`${API_BASE}/sample-report`);
        const data = await res.json();
        body.innerHTML = data.sections
          .map(
            (s) =>
              `<div class="border border-slate-700 rounded-lg p-4 mb-3"><h4 class="text-emerald-400 font-semibold mb-2">${s.title}</h4><p class="text-slate-300 text-sm">${s.body}</p></div>`
          )
          .join("");
        body.dataset.loaded = "1";
      } catch {
        body.innerHTML = '<p class="text-slate-400 text-sm">Connect API for live sample content.</p>';
      }
    });
  });

  document.querySelectorAll("[data-payment-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      paymentMethod = tab.dataset.paymentTab;
      document.querySelectorAll("[data-payment-tab]").forEach((t) => t.classList.toggle("tab-active", t === tab));
      document.querySelectorAll("[data-payment-panel]").forEach((p) => {
        p.classList.toggle("hidden", p.dataset.paymentPanel !== paymentMethod);
      });
    });
  });

  planFull?.addEventListener("change", () => {
    if (planFull.checked) {
      paymentPlan = "full";
      renderTotals();
    }
  });
  planMilestones?.addEventListener("change", () => {
    if (planMilestones.checked && computeTotal() > MILESTONE_MIN) {
      paymentPlan = "milestones";
      renderTotals();
    }
  });

  document.querySelectorAll("[data-copy-wallet]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.copyWallet);
      if (!target) return;
      navigator.clipboard.writeText(target.textContent.trim());
      btn.textContent = "Copied";
      setTimeout(() => {
        btn.textContent = "Copy";
      }, 1500);
    });
  });

  async function loadCatalog() {
    try {
      const res = await fetch(`${API_BASE}/config/parts`);
      if (res.ok) {
        const data = await res.json();
        catalog = data.parts;
      }
    } catch {
      catalog = PARTS_FALLBACK;
    }
    renderPartsGrid();
    renderTotals();
  }

  async function loadWallets() {
    try {
      const res = await fetch(`${API_BASE}/config/payments`);
      if (!res.ok) return;
      const data = await res.json();
      const bep = document.getElementById("bep20-wallet");
      const trc = document.getElementById("trc20-wallet");
      if (bep) bep.textContent = data.usdt_bep20_wallet;
      if (trc) trc.textContent = data.usdt_trc20_wallet;
    } catch {
      /* fallback in HTML */
    }
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    formError.classList.add("hidden");
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting…";

    const payload = {
      client_email: document.getElementById("client-email").value.trim(),
      organization: document.getElementById("organization").value.trim(),
      selected_parts: [...selected],
      target_asset: document.getElementById("target-asset").value.trim(),
      tech_notes: document.getElementById("tech-notes").value.trim() || null,
      payment_plan: paymentPlan,
      payment_method: paymentMethod,
      tx_hash:
        paymentMethod === "usdt_bep20"
          ? document.getElementById("tx-bep20").value.trim()
          : paymentMethod === "usdt_trc20"
            ? document.getElementById("tx-trc20").value.trim()
            : null,
      card_reference:
        paymentMethod === "card_reference"
          ? document.getElementById("card-reference").value.trim()
          : null,
      authorized_scope: document.getElementById("authorized-scope").checked,
    };

    try {
      const res = await fetch(`${API_BASE}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail?.[0]?.msg || data.detail || "Order failed");
      }
      if (!data.payment_verified) {
        throw new Error("Payment could not be verified. Check TxHash or reference.");
      }
      window.location.href = `track.html?order=${encodeURIComponent(data.order_id)}`;
    } catch (err) {
      formError.textContent = err.message || "Submission error";
      formError.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Order & Begin Engineering Intake";
    }
  });

  window.__etharSelectParts = function (partIds) {
    selected.clear();
    partIds.forEach((id) => selected.add(id));
    renderPartsGrid();
    renderTotals();
  };

  loadCatalog();
  loadWallets();
})();
