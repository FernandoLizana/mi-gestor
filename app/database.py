"""URI de base de datos: MySQL en producción (cPanel) o SQLite en local."""

import os
from urllib.parse import quote_plus


def is_sqlite_uri(uri: str) -> bool:
    return uri.startswith("sqlite:")


def build_database_uri(base_dir: str) -> str:
    explicit = os.environ.get("DATABASE_URL", "").strip()
    if explicit:
        return explicit

    host = os.environ.get("DB_HOST", "").strip()
    if host:
        user = os.environ.get("DB_USER", "")
        password = quote_plus(os.environ.get("DB_PASSWORD", ""))
        name = os.environ.get("DB_NAME", "")
        port = os.environ.get("DB_PORT", "3306")
        driver = os.environ.get("DB_DRIVER", "mysql+pymysql")
        return f"{driver}://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"

    db_path = os.path.join(base_dir, "data.sqlite")
    return f"sqlite:///{db_path}"


def database_status(uri: str | None = None) -> dict:
    """Resumen seguro para UI (sin contraseña)."""
    uri = uri or build_database_uri(
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    )
    if is_sqlite_uri(uri):
        path = uri.replace("sqlite:///", "", 1)
        return {
            "backend": "sqlite",
            "label": "SQLite (local)",
            "detail": path,
            "warning": True,
        }
    name = os.environ.get("DB_NAME", "")
    host = os.environ.get("DB_HOST", "localhost")
    return {
        "backend": "mysql",
        "label": f"MySQL · {name}" if name else "MySQL",
        "detail": f"{host} / {name}",
        "warning": False,
    }
