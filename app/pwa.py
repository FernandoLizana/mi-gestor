from flask import Response, jsonify, request, url_for


def register_pwa(app, mount_path=""):
    app.config["CRM_MOUNT_PATH"] = mount_path

    @app.route("/manifest.webmanifest")
    def pwa_manifest():
        from .branding import brand_company, brand_name

        root = request.script_root or mount_path
        icon_192 = url_for("static", filename="icons/icon-192.png")
        icon_512 = url_for("static", filename="icons/icon-512.png")

        manifest = {
            "name": brand_name(),
            "short_name": brand_name()[:12],
            "description": f"Gestor comercial de {brand_company()}",
            "start_url": root + "/",
            "scope": root + "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#181715",
            "theme_color": "#181715",
            "lang": "es",
            "icons": [
                {
                    "src": icon_192,
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": icon_512,
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
            ],
        }
        return jsonify(manifest), 200, {"Content-Type": "application/manifest+json"}

    @app.route("/sw.js")
    def pwa_service_worker():
        root = request.script_root or mount_path
        body = f"""const CACHE = 'crm-dr-v2';
const ROOT = '{root}';
const PRECACHE = [
  ROOT + '/',
  ROOT + '/static/css/style.css',
  ROOT + '/static/js/quickadd.js',
  ROOT + '/static/icons/icon-192.png',
];

self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', (event) => {{
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (!url.pathname.startsWith(ROOT)) return;

  if (url.pathname.startsWith(ROOT + '/static/')) {{
    event.respondWith(
      caches.match(event.request).then((cached) =>
        cached || fetch(event.request).then((res) => {{
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          return res;
        }})
      )
    );
    return;
  }}

  event.respondWith(
    fetch(event.request)
      .then((res) => res)
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match(ROOT + '/')))
  );
}});
"""
        return Response(body, mimetype="application/javascript")
