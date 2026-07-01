function el(tag, opts) {
  opts = opts || {};
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.html != null) node.innerHTML = opts.html; // only for our own trusted markup
  if (opts.attrs) {
    for (const k in opts.attrs) node.setAttribute(k, opts.attrs[k]);
  }
  if (opts.on) {
    for (const ev in opts.on) node.addEventListener(ev, opts.on[ev]);
  }
  return node;
}

function toast(msg, kind) {
  let box = document.getElementById("toast");
  if (!box) {
    box = el("div", { attrs: { id: "toast" } });
    document.body.appendChild(box);
  }
  const item = el("div", { class: "toast-item " + (kind || ""), text: msg });
  box.appendChild(item);
  setTimeout(function () { item.remove(); }, 3500);
}

let _csrf = null;
async function csrfToken() {
  if (_csrf) return _csrf;
  const res = await fetch("/api/csrf", { credentials: "same-origin" });
  if (res.status === 401) { window.location = "/login"; return null; }
  const data = await res.json();
  _csrf = data.csrf_token;
  return _csrf;
}

async function apiFetch(method, url, body) {
  const isWrite = method !== "GET";

  // offline write goes to the queue so it can sync later. check this before
  // asking for a csrf token, because that request would fail offline too and
  // throw before we ever reach the queue. replay grabs a fresh token itself.
  if (isWrite && !navigator.onLine) {
    await OfflineQueue.enqueue({ method: method, url: url, body: body });
    toast("Saved offline, will sync when back online", "ok");
    return { queued: true };
  }

  let res;
  try {
    const headers = { "Content-Type": "application/json" };
    if (isWrite) {
      const tok = await csrfToken();
      if (tok) headers["X-CSRF-Token"] = tok;
    }
    res = await fetch(url, {
      method: method,
      headers: headers,
      credentials: "same-origin",
      body: isWrite ? JSON.stringify(body || {}) : undefined,
    });
  } catch (netErr) {
    // network died mid request, whether on the token fetch or the write.
    // queue writes, rethrow reads
    if (isWrite) {
      await OfflineQueue.enqueue({ method: method, url: url, body: body });
      toast("Saved offline, will sync when back online", "ok");
      return { queued: true };
    }
    throw netErr;
  }

  if (res.status === 401) { window.location = "/login"; return null; }

  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }

  if (!res.ok) {
    const msg = (data && data.error) || ("Request failed (" + res.status + ")");
    throw new Error(msg);
  }
  return data;
}

function wireOfflineBanner() {
  const banner = document.querySelector(".offline-banner");
  if (!banner) return;
  const sync = function () { banner.classList.toggle("show", !navigator.onLine); };
  window.addEventListener("online", sync);
  window.addEventListener("offline", sync);
  sync();
}

function markActiveNav() {
  const here = window.location.pathname;
  document.querySelectorAll(".nav a").forEach(function (a) {
    if (a.getAttribute("href") === here) a.classList.add("active");
  });
}

async function loadUsername() {
  const slot = document.getElementById("nav-username");
  if (!slot) return;
  try {
    const me = await apiFetch("GET", "/api/me");
    if (me && me.username) slot.textContent = me.username;
  } catch (e) { /* not signed in, page guard handles it */ }
}

document.addEventListener("DOMContentLoaded", function () {
  markActiveNav();
  wireOfflineBanner();
  loadUsername();
});
