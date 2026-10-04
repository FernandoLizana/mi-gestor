"""Nombre comercial configurable. No hardcodear la marca en pantallas nuevas."""

import os


def brand_name() -> str:
    return (os.environ.get("BRAND_NAME") or "Mi Gestor").strip() or "Mi Gestor"


def brand_company() -> str:
    return (os.environ.get("BRAND_COMPANY") or brand_name()).strip() or brand_name()


def contact_email() -> str:
    return (os.environ.get("CONTACT_EMAIL") or "").strip()
