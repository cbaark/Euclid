// bug kanban. native html5 drag and drop, PATCH status on drop

(function () {
  let issues = [];

  const COLUMNS = {
    "Urgent": "col-urgent",
    "To-Do": "col-todo",
    "Completed": "col-completed",
  };

  const form = document.getElementById("bug-form");
  const panel = document.getElementById("bug-form-panel");
  const fields = ["title", "description", "status", "priority", "reported_date"];

  function get(id) { return document.getElementById(id); }
  function setError(f, m) { const e = get("err-" + f); if (e) e.textContent = m || ""; }

  function priorityClass(p) {
    return p ? "badge badge-" + p.toLowerCase() : "badge";
  }

  function makeCard(issue) {
    const card = el("div", { class: "bug-card", attrs: { draggable: "true" } });
    const top = el("div", { class: "bc-top" });
    top.appendChild(el("span", { class: "bc-title", text: issue.title }));
    if (issue.priority) top.appendChild(el("span", { class: priorityClass(issue.priority), text: issue.priority }));
    card.appendChild(top);
    if (issue.description) card.appendChild(el("div", { class: "bc-desc", text: issue.description }));
    card.appendChild(el("div", { class: "bc-date", text: "Reported " + (issue.reported_date || "-") }));

    card.addEventListener("dragstart", function (e) {
      e.dataTransfer.setData("text/plain", String(issue.id));
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", function () { card.classList.remove("dragging"); });
    card.addEventListener("click", function () { openEdit(issue.id); });
    return card;
  }

  function render() {
    Object.keys(COLUMNS).forEach(function (status) {
      const body = get(COLUMNS[status]);
      body.textContent = "";
      const cards = issues.filter(function (i) { return i.status === status; });
      if (!cards.length) {
        body.appendChild(el("div", { class: "drop-hint", text: "Drop a card here" }));
      } else {
        cards.forEach(function (i) { body.appendChild(makeCard(i)); });
      }
    });
  }

  // wire each column as a drop target
  function wireColumns() {
    document.querySelectorAll(".column").forEach(function (col) {
      const body = col.querySelector(".col-body");
      const status = col.getAttribute("data-status");
      body.addEventListener("dragover", function (e) { e.preventDefault(); body.classList.add("drag-over"); });
      body.addEventListener("dragleave", function () { body.classList.remove("drag-over"); });
      body.addEventListener("drop", async function (e) {
        e.preventDefault();
        body.classList.remove("drag-over");
        const id = parseInt(e.dataTransfer.getData("text/plain"), 10);
        const issue = issues.find(function (x) { return x.id === id; });
        if (!issue || issue.status === status) return;
        const prev = issue.status;
        issue.status = status; // optimistic
        render();
        try {
          await apiFetch("PATCH", "/api/kanban/" + id, { status: status });
        } catch (err) {
          issue.status = prev; // roll back on failure
          render();
          toast(err.message, "error");
        }
      });
    });
  }

  function showForm(issue) {
    panel.hidden = false;
    get("bug-id").value = issue ? issue.id : "";
    fields.forEach(function (f) { get(f).value = issue ? (issue[f] || "") : ""; });
    if (!issue) {
      get("reported_date").value = new Date().toISOString().slice(0, 10);
      get("status").value = "To-Do";
    }
    get("delete-btn").hidden = !issue;
    get("bug-form-title").textContent = issue ? "EDIT BUG" : "ADD BUG";
    setError("title", ""); setError("status", "");
    panel.scrollIntoView({ behavior: "smooth" });
  }

  function openEdit(id) {
    const issue = issues.find(function (x) { return x.id === id; });
    if (issue) showForm(issue);
  }

  async function load() {
    try {
      issues = await apiFetch("GET", "/api/kanban") || [];
    } catch (e) {
      toast("Could not load bugs", "error");
      return;
    }
    render();
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const payload = {};
    fields.forEach(function (f) { payload[f] = get(f).value.trim(); });
    let ok = true;
    setError("title", ""); setError("status", "");
    if (!payload.title) { setError("title", "Title is required"); ok = false; }
    if (!payload.status) { setError("status", "Status is required"); ok = false; }
    if (!ok) return;

    const id = get("bug-id").value;
    try {
      if (id) await apiFetch("PATCH", "/api/kanban/" + id, payload);
      else await apiFetch("POST", "/api/kanban", payload);
      toast("Bug saved", "ok");
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
    const id = get("bug-id").value;
    if (!id || !confirm("Delete this bug?")) return;
    try {
      await apiFetch("DELETE", "/api/kanban/" + id);
      toast("Bug deleted", "ok");
      panel.hidden = true;
      await load();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    wireColumns();
    load();
  });
  document.addEventListener("euclid:synced", load);
})();
