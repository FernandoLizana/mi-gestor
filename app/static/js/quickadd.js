// Quick-add: maneja los formularios AJAX de los modales rápidos + búsqueda global Ctrl+K
(function () {
  const CRM_BASE = window.CRM_BASE || "";
  // ---------- Forms AJAX ----------
  document.querySelectorAll("form[data-quick-form]").forEach(form => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const stay = document.activeElement && document.activeElement.dataset.stay === "1";
      const stayOnSuccess = form.dataset.stayOnSuccess !== undefined;
      const data = Object.fromEntries(new FormData(form).entries());
      try {
        const r = await fetch(form.dataset.endpoint, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(data),
        });
        const j = await r.json();
        if (!j.ok) { alert(j.error || "Error"); return; }
        toast("Guardado ✓");
        if (stay || stayOnSuccess) {
          form.reset();
          form.querySelector("input,textarea,select")?.focus();
        } else if (j.url) {
          window.location = j.url;
        } else {
          // cerrar modal y refrescar si es la misma página
          bootstrap.Modal.getInstance(form.closest(".modal"))?.hide();
          const path = window.location.pathname;
          if (path.endsWith("/") || path.endsWith("/clientes/") ||
              path.endsWith("/redes/") || path.endsWith("/proyectos/")) {
            setTimeout(() => location.reload(), 400);
          }
        }
      } catch (err) {
        alert("Error de red: " + err.message);
      }
    });
  });

  // ---------- Toast ----------
  function toast(msg) {
    let el = document.createElement("div");
    el.className = "qa-toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.classList.add("show"), 10);
    setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); }, 1800);
  }

  // ---------- Búsqueda global ----------
  const searchModal = document.getElementById("mSearch");
  const input = document.getElementById("qSearchInput");
  const results = document.getElementById("qSearchResults");
  let timer = null, items = [], idx = -1;

  if (searchModal) {
    searchModal.addEventListener("shown.bs.modal", () => input.focus());

    input.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { results.innerHTML = ""; return; }
      timer = setTimeout(() => doSearch(q), 180);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); idx = Math.min(idx + 1, items.length - 1); paint(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); idx = Math.max(idx - 1, 0); paint(); }
      else if (e.key === "Enter") {
        if (idx >= 0 && items[idx]) window.location = items[idx].url;
      }
    });
  }

  async function doSearch(q) {
    const r = await fetch(CRM_BASE + "/q/buscar?q=" + encodeURIComponent(q));
    items = await r.json();
    idx = items.length ? 0 : -1;
    paint();
  }
  function paint() {
    results.innerHTML = items.map((it, i) => `
      <a href="${it.url}" class="list-group-item list-group-item-action ${i===idx?'active':''}">
        <i class="bi bi-${it.icono} me-2"></i>
        <strong>${it.label}</strong>
        <span class="badge bg-secondary float-end">${it.tipo}</span>
      </a>`).join("");
  }

  // ---------- Pre-fill de modales desde botón con data-prefill ----------
  // Uso: <button data-bs-toggle="modal" data-bs-target="#qmPost"
  //              data-prefill='{"proyecto_id":"3","plataforma":"instagram"}'>
  document.addEventListener("show.bs.modal", (ev) => {
    const trigger = ev.relatedTarget;
    if (!trigger || !trigger.dataset || !trigger.dataset.prefill) return;
    let data;
    try { data = JSON.parse(trigger.dataset.prefill); } catch { return; }
    const modal = ev.target;
    Object.entries(data).forEach(([k, v]) => {
      const f = modal.querySelector(`[name="${k}"]`);
      if (f) f.value = v;
    });
  });

  // ---------- Atajos de teclado ----------
  document.addEventListener("keydown", (e) => {
    // Ctrl+K → búsqueda
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      bootstrap.Modal.getOrCreateInstance(document.getElementById("mSearch")).show();
      return;
    }
    // Si estás en un input/textarea, no dispares atajos de letra
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    const map = { n: "fab", c: "qmCliente", p: "qmProyecto",
                  i: "qmInteraccion", b: "qmPost", d: "qmTareaSocial" };
    const id = map[e.key.toLowerCase()];
    if (!id) return;
    if (id === "fab") {
      document.querySelector(".fab")?.click();
    } else {
      e.preventDefault();
      bootstrap.Modal.getOrCreateInstance(document.getElementById(id)).show();
    }
  });
})();
