// when the connection comes back the queue replays against the server.

const OfflineQueue = (function () {
  const DB_NAME = "euclid-offline";
  const STORE = "queue";

  function openDb() {
    return new Promise(function (resolve, reject) {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = function () {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  async function enqueue(item) {
    const db = await openDb();
    return new Promise(function (resolve, reject) {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).add({ ts: Date.now(), item: item });
      tx.oncomplete = function () { resolve(); };
      tx.onerror = function () { reject(tx.error); };
    });
  }

  async function readAll() {
    const db = await openDb();
    return new Promise(function (resolve, reject) {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  async function remove(id) {
    const db = await openDb();
    return new Promise(function (resolve) {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = function () { resolve(); };
    });
  }

  async function replay() {
    if (!navigator.onLine) return;
    const rows = await readAll();
    if (!rows.length) return;

    let tok = null;
    try {
      const r = await fetch("/api/csrf", { credentials: "same-origin" });
      if (r.ok) tok = (await r.json()).csrf_token;
    } catch (e) { return; }

    for (const row of rows) {
      const it = row.item;
      try {
        const res = await fetch(it.url, {
          method: it.method,
          headers: { "Content-Type": "application/json", "X-CSRF-Token": tok },
          credentials: "same-origin",
          body: JSON.stringify(it.body || {}),
        });
        // drop it whether it succeeded or was rejected for good reason,
        // but keep it if the server is unreachable (handled by the throw)
        if (res.ok || res.status < 500) await remove(row.id);
      } catch (e) {
        break;
      }
    }
    if (typeof toast === "function") toast("Offline changes synced", "ok");
    document.dispatchEvent(new CustomEvent("euclid:synced"));
  }

  window.addEventListener("online", replay);
  return { enqueue: enqueue, replay: replay };
})();

// offline + installability
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/service_worker.js", { scope: "/" })
      .then(function () { OfflineQueue.replay(); })
      .catch(function (err) { console.log("sw failed", err); });
  });
}
