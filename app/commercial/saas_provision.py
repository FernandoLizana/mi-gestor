"""Alta de cuentas SaaS desde Mi Gestor (CRM)."""
from __future__ import annotations

import logging
import os
import secrets
import string
from typing import Any

from ..extensions import db
from ..models_commercial import SaasCuenta
from ..models import Cliente, Interaccion
from .saas_constants import (
    SAAS_PORTAL_LABELS,
    normalize_portal_slug,
    portal_acceso_url,
)

log = logging.getLogger("crm.saas")


def generate_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _send_welcome_email(cuenta: SaasCuenta, password_plain: str) -> tuple[bool, str]:
    try:
        from portales_dg.lead_pipeline import send_smtp_message, _notify_recipients
    except ImportError:
        return False, "smtp_no_disponible"

    from ..branding import brand_company

    company = brand_company()
    url = portal_acceso_url(cuenta.portal_slug)
    label = SAAS_PORTAL_LABELS.get(cuenta.portal_slug, cuenta.portal_slug)
    body = "\n".join([
        f"Hola, tu cuenta de {label} está lista.",
        "",
        f"Negocio: {cuenta.nombre_negocio}",
        f"Plan: {cuenta.plan or '—'}",
        "",
        "Acceso al panel:",
        url,
        "",
        f"Usuario: {cuenta.email}",
        f"Contraseña: {password_plain}",
        "",
        "Te recomendamos cambiar la contraseña en tu primer ingreso.",
        "",
        f"— {company}",
    ])
    subject = f"Tu acceso a {label} — {company}"
    return send_smtp_message(
        to_addrs=[cuenta.email],
        subject=subject,
        body=body,
        bcc_addrs=_notify_recipients(),
    )


def ensure_cliente_for_saas(
    *,
    email: str,
    nombre_negocio: str,
    portal_slug: str,
    cliente_id: int | None = None,
    telefono: str | None = None,
) -> tuple[Cliente, bool]:
    """Devuelve (cliente, creado_nuevo). Sin pasar por prospecto ni pipeline."""
    slug = normalize_portal_slug(portal_slug)
    if not slug:
        raise ValueError(f"Portal no soportado: {portal_slug}")

    if cliente_id:
        cliente = Cliente.query.get(cliente_id)
        if cliente:
            return cliente, False

    email_norm = email.strip().lower()
    if not email_norm:
        raise ValueError("El email es obligatorio")

    cliente = Cliente.query.filter(db.func.lower(Cliente.email) == email_norm).first()
    if cliente:
        return cliente, False

    nombre = (nombre_negocio or email_norm).strip()[:150]
    cliente = Cliente(
        nombre=nombre,
        empresa=nombre,
        email=email_norm,
        telefono=(telefono or "").strip() or None,
        estado="activo",
        tipo_registro="cliente",
        estado_pipeline="Cerrado ganado",
        producto_interes=SAAS_PORTAL_LABELS.get(slug),
        fuente="Alta SaaS directa",
    )
    db.session.add(cliente)
    db.session.flush()
    return cliente, True


def create_saas_cuenta_rapido(
    *,
    portal_slug: str,
    nombre_negocio: str,
    email: str,
    password: str | None = None,
    plan: str | None = None,
    notas: str | None = None,
    telefono: str | None = None,
    cliente_id: int | None = None,
    send_email: bool = True,
    vendedor: str | None = None,
) -> tuple[SaasCuenta, str, dict[str, Any], Cliente, bool]:
    """Alta en un paso: crea ficha CRM mínima si hace falta + cuenta portal."""
    cliente, cliente_nuevo = ensure_cliente_for_saas(
        email=email,
        nombre_negocio=nombre_negocio,
        portal_slug=portal_slug,
        cliente_id=cliente_id,
        telefono=telefono,
    )
    cuenta, plain, meta = create_saas_cuenta(
        cliente_id=cliente.id,
        portal_slug=portal_slug,
        nombre_negocio=nombre_negocio,
        email=email,
        password=password,
        plan=plan,
        notas=notas,
        send_email=send_email,
        vendedor=vendedor,
    )
    meta["cliente_nuevo"] = cliente_nuevo
    return cuenta, plain, meta, cliente, cliente_nuevo


def create_saas_cuenta(
    *,
    cliente_id: int,
    portal_slug: str,
    nombre_negocio: str,
    email: str,
    password: str | None = None,
    plan: str | None = None,
    notas: str | None = None,
    send_email: bool = True,
    vendedor: str | None = None,
) -> tuple[SaasCuenta, str, dict[str, Any]]:
    slug = normalize_portal_slug(portal_slug)
    if not slug:
        raise ValueError(f"Portal no soportado: {portal_slug}")

    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        raise ValueError("Cliente no encontrado")

    email_norm = email.strip().lower()
    existing = SaasCuenta.query.filter_by(portal_slug=slug, email=email_norm, activo=True).first()
    if existing:
        raise ValueError(f"Ya existe una cuenta activa para {email_norm} en {slug}")

    plain = password or generate_password()
    cuenta = SaasCuenta(
        cliente_id=cliente_id,
        portal_slug=slug,
        nombre_negocio=nombre_negocio.strip()[:150],
        email=email_norm,
        plan=(plan or "").strip() or None,
        notas=notas,
        estado="activo",
        activo=True,
    )
    cuenta.set_password(plain)
    db.session.add(cuenta)

    cliente.estado = "activo"
    cliente.tipo_registro = "cliente"
    if not cliente.producto_interes:
        cliente.producto_interes = SAAS_PORTAL_LABELS.get(slug)

    db.session.add(
        Interaccion(
            cliente_id=cliente_id,
            canal="sistema",
            tipo="saas",
            resumen=f"Cuenta SaaS creada: {SAAS_PORTAL_LABELS.get(slug)} — {cuenta.email}",
            usuario_responsable=vendedor,
        )
    )
    db.session.flush()

    meta: dict[str, Any] = {"email_sent": False, "email_status": "skipped"}
    if send_email:
        ok, status = _send_welcome_email(cuenta, plain)
        meta = {"email_sent": ok, "email_status": status}

    return cuenta, plain, meta


def portal_slug_from_producto(producto: str | None) -> str | None:
    return normalize_portal_slug(producto or "")
