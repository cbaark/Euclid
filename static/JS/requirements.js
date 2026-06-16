(function () {
  let reqs = [];

  const form = document.getElementById("req-form");
  const panel = document.getElementById("req-form-panel");
  const body = document.getElementById("req-body");
  const editable = ["type", "description", "priority", "status", "assigned_module",
                    "source_stakeholder", "acceptance_criteria"];

  function get(id) { return document.getElementById(id); }
  function setError(f, m) { const e = get("err-" + f); if (e) e.textContent = m || ""; }

  function statusClass(s) { return "badge badge-" + s.toLowerCase().replace(/ /g, "-"); }
  function priorityClass(p) { return p ? "badge badge-" + p.toLowerCase() : "badge"; }

  function updateOverview() {
    const total = reqs.length;
    const done = reqs.filter(function (r) { return r.status === "Complete"; }).length;
    const prog = reqs.filter(function (r) { return r.status === "In Progress"; }).length;
    const not = reqs.filter(function (r) { return r.status === "Not Started"; }).length;
    get("cnt-complete").textContent = done;
    get("cnt-progress").textContent = prog;
    get("cnt-notstarted").textContent = not;
    get("progress-fill").style.width = (total ? Math.round((done / total) * 100) : 0) + "%";
  }

  function render() {
    body.textContent = "";
    if (!reqs.length) {
      const tr = el("tr");
      const td = el("td", { class: "empty", text: "No requirements yet", attrs: { colspan: "7" } });
      tr.appendChild(td);
      body.appendChild(tr);
      updateOverview();
      return;
    }
    reqs.forEach(function (r) {
      const tr = el("tr");
      tr.appendChild(el("td", { class: "id-cell", text: r.req_id }));
      tr.appendChild(el("td", { class: "desc-cell", text: r.description || "" }));
      tr.appendChild(el("td", { text: r.type ? r.type.replace(/.*\((.*)\)/, "$1") : "" }));
      const pc = el("td"); if (r.priority) pc.appendChild(el("span", { class: priorityClass(r.priority), text: r.priority })); tr.appendChild(pc);
      const sc = el("td"); if (r.status) sc.appendChild(el("span", { class: statusClass(r.status), text: r.status })); tr.appendChild(sc);
      tr.appendChild(el("td", { text: r.assigned_module || "" }));
      const ac = el("td");
      ac.appendChild(el("button", { class: "btn btn-sm", text: "Edit", on: { click: function () { openEdit(r.id); } } }));
      tr.appendChild(ac);
      body.appendChild(tr);
    });
    updateOverview();
  }

  function showForm(r) {
    panel.hidden = false;
    get("req-row-id").value = r ? r.id : "";
    get("req_id_display").value = r ? r.req_id : "";
    editable.forEach(function (f) { get(f).value = r ? (r[f] || "") : ""; });
    if (!r) get("status").value = "Not Started";
    get("delete-btn").hidden = !r;
    get("req-form-title").textContent = r ? "EDIT REQUIREMENT" : "ADD REQUIREMENT";
    setError("type", ""); setError("description", "");
    panel.scrollIntoView({ behavior: "smooth" });
  }

  function openEdit(id) {
    const r = reqs.find(function (x) { return x.id === id; });
    if (r) showForm(r);
  }

  async function load() {
    try {
      reqs = await apiFetch("GET", "/api/requirements") || [];
    } catch (e) {
      toast("Could not load requirements", "error");
      return;
    }
    render();
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const payload = {};
    editable.forEach(function (f) { payload[f] = get(f).value.trim(); });
    let ok = true;
    setError("type", ""); setError("description", "");
    if (!payload.type) { setError("type", "Type is required"); ok = false; }
    if (!payload.description) { setError("description", "Description is required"); ok = false; }
    if (!ok) return;

    const id = get("req-row-id").value;
    try {
      if (id) await apiFetch("PATCH", "/api/requirements/" + id, payload);
      else await apiFetch("POST", "/api/requirements", payload);
      toast("Requirement saved", "ok");
      panel.hidden = true;
      await load();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  get("add-btn").addEventListener("click", function () { showForm(null); });
  get("close-form").addEventListener("click", function () { panel.hidden = true; });
  get("cancel-btn").addEventListener("click", function () { panel.hidden = true; });

  get("delete-btn").addEventListener("click", async function () {
    const id = get("req-row-id").value;
    if (!id || !confirm("Delete this requirement?")) return;
    try {
      await apiFetch("DELETE", "/api/requirements/" + id);
      toast("Requirement deleted", "ok");
      panel.hidden = true;
      await load();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.addEventListener("DOMContentLoaded", load);
  document.addEventListener("euclid:synced", load);
})();
