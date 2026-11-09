/* WearVerse service worker: keeps the app shell available offline so the POS opens without internet.
   API calls are never cached here (the POS keeps its own data in IndexedDB). */
const CACHE = "wearverse-shell-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/pos", "/manifest.webmanifest", "/icon.svg"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (event.request.mode === "navigate") {
    // Network first for pages, fall back to the cached shell when offline.
    event.respondWith(fetch(event.request).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(event.request, copy));
      return res;
    }).catch(() => caches.match(event.request).then((r) => r || caches.match("/pos") || caches.match("/"))));
    return;
  }
  if (url.pathname.startsWith("/assets/")) {
    // Built assets have content hashes: cache first.
    event.respondWith(caches.match(event.request).then((hit) => hit || fetch(event.request).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(event.request, copy));
      return res;
    })));
  }
});
