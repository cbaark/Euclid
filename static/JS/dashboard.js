// dashboard: pull the summary stats and the recent activity feed

(function () {
  const KIND_LABEL = {
    journal: "Journal entry",
    kanban: "Bug",
    reference: "Reference",
    requirement: "Requirement",
  };

  async function load() {
    let d;
    try {
      d = await apiFetch("GET", "/api/dashboard");
    } catch (e) {
      toast("Could not load dashboard", "error");
      return;
    }
    if (!d) return;

    document.getElementById("stat-journal").textContent = d.journal_count;
    document.getElementById("stat-urgent").textContent = d.urgent_bugs;
    document.getElementById("stat-req").textContent = d.requirements_done + " / " + d.requirements_total;
    document.getElementById("stat-ref").textContent = d.reference_count;

    // little preview blurbs on each module card
    document.getElementById("card-journal").textContent = d.journal_count + " entries logged";
    document.getElementById("card-kanban").textContent = d.urgent_bugs + " urgent bug(s) open";
    document.getElementById("card-req").textContent = d.requirements_done + " of " + d.requirements_total + " complete";
    document.getElementById("card-ref").textContent = d.reference_count + " references saved";

    const list = document.getElementById("activity");
    list.textContent = "";
    if (!d.recent_activity.length) {
      list.appendChild(el("li", { class: "empty", text: "No activity yet" }));
      return;
    }
    d.recent_activity.forEach(function (a) {
      const li = el("li");
      li.appendChild(el("span", { class: "tag", text: KIND_LABEL[a.kind] || a.kind }));
      li.appendChild(el("span", { text: a.label }));
      list.appendChild(li);
    });
  }

  document.addEventListener("DOMContentLoaded", load);
  document.addEventListener("euclid:synced", load);
})();
