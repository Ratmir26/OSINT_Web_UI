const CACHE = "osint-web-ui-v1";
const ASSETS = [
    "/",
    "/static/css/style.css",
    "/static/js/main.js",
    "/static/icon-192.png",
    "/static/icon-512.png",
];

self.addEventListener("install", (e) => {
    e.waitUntil(
        caches.open(CACHE).then((c) => c.addAll(ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (e) => {
    if (e.request.url.startsWith(self.location.origin)) {
        e.respondWith(
            caches.match(e.request).then((cached) => {
                const fetched = fetch(e.request).then((res) => {
                    if (res.ok && e.request.method === "GET") {
                        const clone = res.clone();
                        caches.open(CACHE).then((c) => c.put(e.request, clone));
                    }
                    return res;
                }).catch(() => cached);
                return cached || fetched;
            })
        );
    }
});
