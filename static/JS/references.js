
(function () {
  let refs = [];
  let filter = "ALL";

  const form = document.getElementById("ref-form");
  const panel = document.getElementById("ref-form-panel");
  const body = document.getElementById("ref-body");
  const editable = ["title", "ref_type", "url", "tags", "date_added", "related_module", "notes"];

  function get(id) { return document.getElementById(id); }
  function setError(f, m) { const e = get("err-" + f); if (e) e.textContent = m || ""; }

  function render() {
    body.textContent = "";
    const shown = refs.filter(function (r) { return filter === "ALL" || r.ref_type === filter; });
    if (!shown.length) {
      const tr = el("tr");
      tr.appendChild(el("td", { class: "empty", text: "No references here", attrs: { colspan: "5" } }));
      body.appendChild(tr);
      return;
    }
    shown.forEach(function (r) {
      const tr = el("tr");
      const titleCell = el("td");
      titleCell.appendChild(el("div", { class: "r-title", text: r.title }));
      if (r.url) {
        const wrap = el("div", { class: "r-url" });
        // href is set as an attribute, text stays as textContent so nothing executes
        wrap.appendChild(el("a", { text: r.url, attrs: { href: r.url, target: "_blank", rel: "noopener noreferrer" } }));
        titleCell.appendChild(wrap);
      }
      tr.appendChild(titleCell);
      tr.appendChild(el("td", { text: r.ref_type || "" }));
      tr.appendChild(el("td", { text: r.tags || "" }));
      tr.appendChild(el("td", { text: r.date_added || "" }));
      const ac = el("td");
      ac.appendChild(el("button", { class: "btn btn-sm", text: "Edit", on: { click: function () { openEdit(r.id); } } }));
      tr.appendChild(ac);
      body.appendChild(tr);
    });
  }

  function showForm(r) {
    panel.hidden = false;
    get("ref-row-id").value = r ? r.id : "";
    editable.forEach(function (f) { get(f).value = r ? (r[f] || "") : ""; });
    if (!r) get("date_added").value = new Date().toISOString().slice(0, 10);
    get("delete-btn").hidden = !r;
    get("ref-form-title").textContent = r ? "EDIT REFERENCE" : "ADD REFERENCE";
    setError("title", ""); setError("url", "");
    panel.scrollIntoView({ behavior: "smooth" });
  }

  function openEdit(id) {
    const r = refs.find(function (x) { return x.id === id; });
    if (r) showForm(r);
  }

  async function load() {
    try {
      refs = await apiFetch("GET", "/api/references") || [];
    } catch (e) {
      toast("Could not load references", "error");
      return;
    }
    render();
  }

  // quick client check, server still validates
  function looksLikeUrl(u) {
    return /^https?:\/\/.+/i.test(u);
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const payload = {};
    editable.forEach(function (f) { payload[f] = get(f).value.trim(); });
    let ok = true;
    setError("title", ""); setError("url", "");
    if (!payload.title) { setError("title", "Title is required"); ok = false; }
    if (payload.url && !looksLikeUrl(payload.url)) {
      setError("url", "URL must start with http:// or https://"); ok = false;
    }
    if (!ok) return;

    const id = get("ref-row-id").value;
    try {
      if (id) await apiFetch("PATCH", "/api/references/" + id, payload);
      else await apiFetch("POST", "/api/references", payload);
      toast("Reference saved", "ok");
      panel.hidden = true;
      await load();
    } catch (e) {
      // surface duplicate url right on the field
      if (e.message && e.message.toLowerCase().indexOf("url") !== -1) setError("url", e.message);
      toast(e.message, "error");
    }
  });

  document.getElementById("tabs").addEventListener("click", function (e) {
    if (!e.target.classList.contains("tab")) return;
    document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
    e.target.classList.add("active");
    filter = e.target.getAttribute("data-type");
    render();
  });

  get("add-btn").addEventListener("click", function () { showForm(null); });
  get("close-form").addEventListener("click", function () { panel.hidden = true; });
  get("cancel-btn").addEventListener("click", function () { panel.hidden = true; });

  get("delete-btn").addEventListener("click", async function () {
    const id = get("ref-row-id").value;
    if (!id || !confirm("Delete this reference?")) return;
    try {
      await apiFetch("DELETE", "/api/references/" + id);
      toast("Reference deleted", "ok");
      panel.hidden = true;
      await load();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.addEventListener("DOMContentLoaded", load);
  document.addEventListener("euclid:synced", load);
})();
