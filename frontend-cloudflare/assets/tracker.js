(function () {
  const API_BASE = window.AGENCY_API_BASE || "http://localhost:8000/api/v1";
  const params = new URLSearchParams(window.location.search);
  const input = document.getElementById("order-search");
  const loadBtn = document.getElementById("load-order");
  const timeline = document.getElementById("timeline");
  const meta = document.getElementById("order-meta");
  const invoice = document.getElementById("invoice-panel");
  const milestonesPanel = document.getElementById("milestones-panel");
  const progressBar = document.getElementById("progress-bar");
  const progressLabel = document.getElementById("progress-label");
  const summary = document.getElementById("executive-summary");
  const downloadBtn = document.getElementById("download-report");
  const pollStatus = document.getElementById("poll-status");
  const errorBox = document.getElementById("track-error");
  const milestoneForm = document.getElementById("milestone-pay-form");
  const milestoneError = document.getElementById("milestone-error");

  let currentOrder = params.get("order") || "";
  let pollTimer = null;
  let paymentMethod = "card_reference";

  if (input && currentOrder) input.value = currentOrder;

  const STAGES = [
    { n: 1, title: "Intake & Scope Verified" },
    { n: 2, title: "Security & Configuration Audit" },
    { n: 3, title: "Remediation & Patch Synthesis" },
    { n: 4, title: "Principal Engineer QA & Sign-Off" },
  ];

  function statusLabel(status) {
    const map = {
      PENDING_VERIFICATION: "Pending Payment Verification",
      IN_PROGRESS: "Engineering In Progress",
      AWAITING_PAYMENT: "Awaiting Milestone Payment",
      AWAITING_ADMIN_APPROVAL: "Awaiting Principal Sign-Off",
      COMPLETED: "Completed — Report Released",
      FAILED: "Processing Failed",
    };
    return map[status] || status;
  }

  function renderProgress(order) {
    const pct = order.progress_percent ?? 0;
    if (progressBar) progressBar.style.width = `${pct}%`;
    if (progressLabel) progressLabel.textContent = `${pct}% complete across engineering desks`;
  }

  function renderInvoice(order) {
    if (!invoice) return;
    const lines = (order.line_items || [])
      .map(
        (li) =>
          `<tr class="border-b border-slate-800"><td class="py-2 text-slate-400">${li.part_id}</td><td class="py-2">${li.title}</td><td class="py-2 text-right">$${Number(li.line_total_usd).toFixed(2)}</td></tr>`
      )
      .join("");
    invoice.innerHTML = `
      <table class="w-full text-sm"><thead><tr class="text-slate-500"><th class="text-left pb-2">Part</th><th class="text-left pb-2">Description</th><th class="text-right pb-2">Fee</th></tr></thead>
      <tbody>${lines}</tbody>
      <tfoot><tr><td colspan="2" class="pt-3 font-semibold">Total</td><td class="pt-3 text-right text-emerald-400 font-bold">$${Number(order.total_amount).toFixed(2)}</td></tr>
      <tr><td colspan="2" class="text-slate-400">Paid to date</td><td class="text-right">$${Number(order.paid_amount).toFixed(2)}</td></tr>
      <tr><td colspan="2" class="text-slate-400">Balance due</td><td class="text-right text-cyan-400">$${Number(order.amount_due_now).toFixed(2)}</td></tr></tfoot></table>`;
  }

  function renderMilestones(order) {
    if (!milestonesPanel) return;
    const rows = (order.milestones || [])
      .map(
        (m) =>
          `<li class="flex justify-between items-center py-2 border-b border-slate-800 text-sm">
            <span>${m.label} ${m.paid ? '<span class="text-emerald-400 ml-2">Paid</span>' : ""}</span>
            <span>$${Number(m.amount_usd).toFixed(2)}</span>
          </li>`
      )
      .join("");
    milestonesPanel.innerHTML = `<ul>${rows}</ul><p class="text-xs text-slate-500 mt-2">Plan: ${order.payment_plan === "milestones" ? "3-Part Milestone" : "Full Upfront"}</p>`;

    const showPay =
      order.next_milestone &&
      !order.next_milestone.paid &&
      (order.status === "AWAITING_PAYMENT" || order.status === "IN_PROGRESS" || order.status === "AWAITING_ADMIN_APPROVAL");
    if (milestoneForm) {
      milestoneForm.classList.toggle("hidden", !showPay || order.payment_plan === "full" || !order.next_milestone);
      const dueEl = document.getElementById("milestone-due-label");
      if (dueEl && order.next_milestone) {
        dueEl.textContent = `${order.next_milestone.label} — $${Number(order.next_milestone.amount_usd).toFixed(2)}`;
      }
    }
  }

  function renderTimeline(order) {
    const logsByStage = {};
    (order.stage_logs || []).forEach((log) => {
      if (!logsByStage[log.stage]) logsByStage[log.stage] = [];
      logsByStage[log.stage].push(log);
    });
    timeline.innerHTML = STAGES.map((stage) => {
      const active = order.current_stage >= stage.n;
      const complete = order.current_stage > stage.n || (order.current_stage === stage.n && ["AWAITING_ADMIN_APPROVAL", "COMPLETED"].includes(order.status));
      const logs = (logsByStage[stage.n] || [])
        .map((l) => `<li class="text-xs text-slate-400 mt-1">${new Date(l.timestamp).toLocaleString()} — ${l.message}</li>`)
        .join("");
      return `<div class="relative pl-8 pb-8 border-l ${active ? "border-emerald-500/60" : "border-slate-700"} last:border-0 last:pb-0">
        <span class="absolute -left-2.5 top-0 w-5 h-5 rounded-full ${complete ? "bg-emerald-500" : active ? "bg-cyan-500 animate-pulse" : "bg-slate-700"}"></span>
        <h3 class="font-semibold">${stage.title}</h3>
        <ul class="mt-2">${logs}</ul>
      </div>`;
    }).join("");
  }

  function renderOrder(order) {
    errorBox.classList.add("hidden");
    meta.innerHTML = `
      <div class="grid md:grid-cols-2 gap-4 text-sm">
        <div><span class="text-slate-500">Order</span><p class="font-mono text-cyan-400">${order.order_code}</p></div>
        <div><span class="text-slate-500">Organization</span><p>${order.organization}</p></div>
        <div><span class="text-slate-500">Status</span><p class="text-emerald-400">${statusLabel(order.status)}</p></div>
        <div><span class="text-slate-500">Posture</span><p>${order.posture_score != null ? order.posture_score + "/100" : "Pending"}</p></div>
        <div class="md:col-span-2"><span class="text-slate-500">Target</span><p class="break-all text-slate-300">${order.target_asset}</p></div>
      </div>`;
    renderProgress(order);
    renderInvoice(order);
    renderMilestones(order);
    renderTimeline(order);

    if (order.executive_summary) {
      summary.classList.remove("hidden");
      summary.querySelector("pre").textContent = order.executive_summary;
    } else summary.classList.add("hidden");

    if (order.report_available) {
      downloadBtn.classList.remove("hidden");
      downloadBtn.href = `${API_BASE}/orders/${encodeURIComponent(order.order_code)}/report`;
    } else downloadBtn.classList.add("hidden");

    const keepPolling = !["COMPLETED", "FAILED"].includes(order.status);
    pollStatus.textContent = keepPolling ? "Live sync active…" : "Synchronized.";
    if (keepPolling && !pollTimer) pollTimer = setInterval(() => fetchOrder(currentOrder, true), 5000);
    if (!keepPolling && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function fetchOrder(code, silent) {
    if (!code) {
      errorBox.textContent = "Enter order ID (ORD-XXXX).";
      errorBox.classList.remove("hidden");
      return;
    }
    currentOrder = code.trim().toUpperCase();
    try {
      const res = await fetch(`${API_BASE}/orders/${encodeURIComponent(currentOrder)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Not found");
      renderOrder(data);
      const url = new URL(window.location.href);
      url.searchParams.set("order", currentOrder);
      window.history.replaceState({}, "", url);
    } catch (err) {
      if (!silent) {
        errorBox.textContent = err.message;
        errorBox.classList.remove("hidden");
      }
    }
  }

  document.querySelectorAll("[data-payment-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      paymentMethod = tab.dataset.paymentTab;
      document.querySelectorAll("[data-payment-tab]").forEach((t) => t.classList.toggle("tab-active", t === tab));
      document.querySelectorAll("[data-payment-panel]").forEach((p) => {
        p.classList.toggle("hidden", p.dataset.paymentPanel !== paymentMethod);
      });
    });
  });

  milestoneForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    milestoneError.classList.add("hidden");
    const payload = {
      payment_method: paymentMethod,
      tx_hash:
        paymentMethod === "usdt_bep20"
          ? document.getElementById("ms-tx-bep20").value.trim()
          : paymentMethod === "usdt_trc20"
            ? document.getElementById("ms-tx-trc20").value.trim()
            : null,
      card_reference:
        paymentMethod === "card_reference" ? document.getElementById("ms-card-ref").value.trim() : null,
    };
    try {
      const res = await fetch(`${API_BASE}/orders/${encodeURIComponent(currentOrder)}/milestones/pay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Payment failed");
      await fetchOrder(currentOrder, true);
    } catch (err) {
      milestoneError.textContent = err.message;
      milestoneError.classList.remove("hidden");
    }
  });

  loadBtn?.addEventListener("click", () => fetchOrder(input.value, false));
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") fetchOrder(input.value, false);
  });

  if (currentOrder) fetchOrder(currentOrder, false);
})();
