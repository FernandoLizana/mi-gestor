"""Carga opcional de PixelWall si PIXELWALL_APP_DIR apunta a esa app."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

PIXELWALL_URL_PREFIX = "/proyectos/i-d/pixelwall"
_app = None


def _pixelwall_dir() -> Path:
    configured = os.environ.get("PIXELWALL_APP_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path()


def load_pixelwall_app():
    global _app
    if _app is not None:
        return _app

    app_dir = _pixelwall_dir()
    if not (app_dir / "app.py").is_file():
        raise FileNotFoundError(
            "La app externa no está en este repositorio. Define PIXELWALL_APP_DIR si quieres montarla."
        )

    source = str(app_dir.resolve())
    if source not in sys.path:
        sys.path.insert(0, source)

    spec = importlib.util.spec_from_file_location("pixelwall_hp_app", app_dir / "app.py")
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar la app externa.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app = mod.app
    app.root_path = source
    app.template_folder = str(app_dir / "templates")
    app.static_folder = str(app_dir / "static")
    mod.init_app()
    _app = app
    return _app


class LazyPixelwallWSGI:
    """App WSGI sin middleware extra (DispatcherMiddleware ya ajusta SCRIPT_NAME)."""

    def __call__(self, environ, start_response):
        return load_pixelwall_app()(environ, start_response)


def lazy_pixelwall_application():
    return LazyPixelwallWSGI()
