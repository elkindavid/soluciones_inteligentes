const CACHE_NAME = "destajos-cache-v12";
const PRECACHE_URLS = [
  "/static/css/tailwind.min.css",
  "/static/images/logo-192.png",
  "/static/images/logo-512.png",
  "/static/images/logo.png",
  "/static/images/fallback.png",
  "/static/js/alpine.min.js",
  "/static/js/indexedDB.js",
  "/static/manifest.json",
  "/static/screenshots/screenshot1.png",
  "/static/screenshots/screenshot2.png",
  "/static/offline.html"
];

// ---------------------------
// Instalación: cachear recursos estáticos
// ---------------------------
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return Promise.allSettled(
        PRECACHE_URLS.map(url => cache.add(url).catch(err => {
          console.warn("⚠️ No se pudo cachear:", url, err);
        }))
      );
    }).then(() => self.skipWaiting())
  );
});

// ---------------------------
// Activación: limpiar caches antiguas
// ---------------------------
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ---------------------------
// Fetch: manejo de rutas
// ---------------------------
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  // No interceptar rutas de login/logout ni la raíz
  if (url.pathname === "/" || url.pathname === "/auth/login" || url.pathname === "/auth/logout") return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Si el recurso es un redirect, no interferir
        if (response.type === "opaqueredirect" || (response.status >= 300 && response.status < 400)) {
          return response; // dejar que el navegador lo maneje
        }
        return response;
      })
      .catch(() => {
        // Fallback para HTML
        if (event.request.destination === "document") {
          return caches.match("/static/offline.html");
        }
        // Fallback para imágenes
        if (event.request.destination === "image") {
          return caches.match("/static/images/fallback.png");
        }
        // Otros recursos: mensaje de error
        return new Response("Sin conexión y recurso no disponible en caché", {
          status: 503,
          headers: { "Content-Type": "text/plain" }
        });
      })
  );
});
