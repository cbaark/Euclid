// developer journal. full CRUD, plain text content, no markdown

(function () {
  let entries = [];
  let selectedId = null;

  const form = document.getElementById("journal-form");
  const listEl = document.getElementById("entry-list");
  const search = document.getElementById("search");

  const fields = ["title", "date", "project_tag", "entry_type", "related_module", "content"];

  function get(id) { return document.getElementById(id); }
  function setError(f, m) { const e = get("err-" + f); if (e) e.textContent = m || ""; }
  function clearErrors() { ["title", "date", "content"].forEach(function (f) { setError(f, ""); }); }

  function render() {
    const q = search.value.trim().toLowerCase();
    listEl.textContent = "";
    const shown = entries.filter(function (e) {
      if (!q) return true;
      return (e.title + " " + (e.project_tag || "") + " " + (e.content || "")).toLowerCase().indexOf(q) !== -1;
    });
    if (!shown.length) {
      listEl.appendChild(el("li", { class: "empty", text: "No entries yet" }));
      return;
    }
    shown.forEach(function (e) {
      const li = el("li", { class: e.id === selectedId ? "active" : "" });
      li.appendChild(el("div", { class: "e-title", text: e.title }));
      const meta = e.date + (e.entry_type ? " - " + e.entry_type : "");
      li.appendChild(el("div", { class: "e-meta", text: meta }));
      li.addEventListener("click", function () { selectEntry(e.id); });
      listEl.appendChild(li);
    });
  }

  function fillForm(e) {
    get("entry-id").value = e ? e.id : "";
    fields.forEach(function (f) { get(f).value = e ? (e[f] || "") : ""; });
    if (!e) get("date").value = new Date().toISOString().slice(0, 10);
    get("delete-btn").hidden = !e;
    get("form-title").textContent = e ? "EDIT JOURNAL ENTRY" : "NEW JOURNAL ENTRY";
    clearErrors();
  }

  function selectEntry(id) {
    selectedId = id;
    const e = entries.find(function (x) { return x.id === id; });
    fillForm(e);
    render();
  }

  function newEntry() {
    selectedId = null;
    fillForm(null);
    render();
  }

  async function load() {
    try {
      entries = await apiFetch("GET", "/api/journal") || [];
    } catch (e) {
      toast("Could not load entries", "error");
      return;
    }
    render();
  }

  function validate(payload) {
    let ok = true;
    clearErrors();
    if (!payload.title) { setError("title", "Title is required"); ok = false; }
    if (!payload.date) { setError("date", "Date is required"); ok = false; }
    if (!payload.content) { setError("content", "Content is required"); ok = false; }
    return ok;
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const payload = {};
    fields.forEach(function (f) { payload[f] = get(f).value.trim(); });
    if (!validate(payload)) return;

    const id = get("entry-id").value;
    try {
      if (id) {
        await apiFetch("PATCH", "/api/journal/" + id, payload);
      } else {
        await apiFetch("POST", "/api/journal", payload);
      }
      toast("Entry saved", "ok");
      newEntry();
      await load();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  get("new-btn").addEventListener("click", newEntry);
  get("cancel-btn").addEventListener("click", newEntry);

  get("delete-btn").addEventListener("click", async function () {
    const id = get("entry-id").value;
    if (!id) return;
    if (!confirm("Delete this journal entry?")) return;
    try {
      await apiFetch("DELETE", "/api/journal/" + id);
      toast("Entry deleted", "ok");
      newEntry();
      await load();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  search.addEventListener("input", render);

  document.addEventListener("DOMContentLoaded", function () {
    fillForm(null);
    load();
  });
  document.addEventListener("euclid:synced", load);
})();
