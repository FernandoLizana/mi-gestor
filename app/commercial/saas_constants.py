"""Portales de ejemplo. Los slugs se pueden ampliar en este archivo."""

SAAS_PORTAL_SLUGS = (
    "agenda",
    "sitio-web",
    "campanas",
)

SAAS_PORTAL_LABELS = {
    "agenda": "Agenda de reservas",
    "sitio-web": "Sitio web",
    "campanas": "Campañas",
}

PRODUCT_TO_PORTAL_SLUG = {
    "agenda": "agenda",
    "agenda de reservas": "agenda",
    "sitio-web": "sitio-web",
    "sitio web": "sitio-web",
    "campanas": "campanas",
    "campañas": "campanas",
}


def normalize_portal_slug(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    if key in SAAS_PORTAL_SLUGS:
        return key
    return PRODUCT_TO_PORTAL_SLUG.get(key)


def portal_mount_path(slug: str) -> str:
    return f"/portal/{slug}"


def portal_acceso_url(slug: str, base_url: str | None = None) -> str:
    import os

    base = (base_url or os.environ.get("APP_URL", "")).rstrip("/")
    path = f"{portal_mount_path(slug)}/acceso"
    return f"{base}{path}" if base else path
