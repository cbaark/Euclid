// Euclid service worker. precache the app shell, then serve assets cache-first
// and api reads network-first with a cache fallback so the app still opens offline.

const CACHE = "euclid-v2";

const SHELL = [
  "/",
  "/login",
  "/register",
  "/dashboard",
  "/journal",
  "/kanban",
  "/requirements",
  "/references",
  "/manifest.json",
  "/static/css/base.css",
  "/static/css/auth.css",
  "/static/css/dashboard.css",
  "/static/css/journal.css",
  "/static/css/kanban.css",
  "/static/css/requirements.css",
  "/static/css/references.css",
  "/static/js/utils.js",
  "/static/js/offline.js",
  "/static/js/login.js",
  "/static/js/register.js",
  "/static/js/dashboard.js",
  "/static/js/journal.js",
  "/static/js/kanban.js",
  "/static/js/requirements.js",
  "/static/js/references.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      // addAll fails the whole install if one url 404s, so add them one by one
      return Promise.all(SHELL.map(function (url) {
        return cache.add(url).catch(function () { /* skip anything missing */ });
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

// only cache plain, non redirected, same origin 200s
function cacheable(res) {
  return res && res.ok && !res.redirected && res.type === "basic";
}

self.addEventListener("fetch", function (event) {
  const req = event.request;
  if (req.method !== "GET") return; // writes go through the offline queue, not here

  const url = new URL(req.url);

  // page navigations: go to the network and let the browser handle redirects
  // (login bounces etc). only fall back to cache when we are actually offline.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(function () {
        return caches.match(req).then(function (hit) { return hit || caches.match("/login"); });
      })
    );
    return;
  }

  // api reads: network first, fall back to whatever we cached
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(req).then(function (res) {
        if (cacheable(res)) {
          const copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match(req);
      })
    );
    return;
  }

  // static assets: cache first, then network
  event.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (cacheable(res)) {
          const copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      });
    })
  );
});
