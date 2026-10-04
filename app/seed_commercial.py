import json
import os

from .extensions import db
from .models import ConfigComision, PlantillaMensaje, ProductoCatalogo


PRODUCTOS = [
    {
        "slug": "agenda",
        "nombre": "Agenda de reservas",
        "descripcion": "Reservas, horarios y recordatorios para negocios de servicios.",
        "precio_mensual_sugerido": 29990,
        "setup_sugerido": 80000,
        "nicho": "servicios",
        "planes": [
            {"nombre": "Inicial", "setup": 50000, "mensualidad": 19990},
            {"nombre": "Pro", "setup": 80000, "mensualidad": 29990},
            {"nombre": "Equipo", "setup": 120000, "mensualidad": 49990},
        ],
    },
    {
        "slug": "sitio-web",
        "nombre": "Sitio web",
        "descripcion": "Sitio de presentación con contacto, servicios y formulario.",
        "precio_mensual_sugerido": 19990,
        "setup_sugerido": 150000,
        "nicho": "presencia web",
    },
    {
        "slug": "campanas",
        "nombre": "Campañas",
        "descripcion": "Plan de contenidos y pauta para redes.",
        "precio_mensual_sugerido": 39990,
        "setup_sugerido": 0,
        "nicho": "marketing",
    },
    {
        "slug": "otro",
        "nombre": "Otro",
        "descripcion": "Otro producto o servicio.",
        "nicho": "general",
    },
]

PLANTILLAS_BASE = [
    {
        "producto": "Agenda de reservas",
        "canal": "WhatsApp",
        "etapa": "primer contacto",
        "titulo": "Primer contacto",
        "cuerpo": (
            "Hola {{nombre_contacto}}, vi {{nombre_negocio}} en {{comuna}}. "
            "Soy {{vendedora}} de {{marca}}. Ayudamos a ordenar reservas sin depender solo del WhatsApp. "
            "¿Te interesaría ver una demo breve de {{producto}}?"
        ),
    },
    {
        "producto": "Sitio web",
        "canal": "WhatsApp",
        "etapa": "primer contacto",
        "titulo": "Primer contacto sitio",
        "cuerpo": (
            "Hola {{nombre_contacto}}, soy {{vendedora}} de {{marca}}. "
            "Armamos {{producto}} para que {{nombre_negocio}} tenga servicios, contacto y un formulario en un solo lugar. "
            "¿Te muestro un ejemplo?"
        ),
    },
    {
        "producto": "Agenda de reservas",
        "canal": "WhatsApp",
        "etapa": "seguimiento 48 horas",
        "titulo": "Seguimiento",
        "cuerpo": (
            "Hola {{nombre_contacto}}, te escribo de nuevo por {{nombre_negocio}}. "
            "Quedó pendiente mostrarte {{producto}}. ¿Tienes 10 minutos esta semana?"
        ),
    },
    {
        "producto": "Campañas",
        "canal": "WhatsApp",
        "etapa": "primer contacto",
        "titulo": "Primer contacto campañas",
        "cuerpo": (
            "Hola {{nombre_contacto}}, soy {{vendedora}} de {{marca}}. "
            "Con {{producto}} dejamos un plan de contenidos y pauta para {{nombre_negocio}}. "
            "¿Te parece una llamada corta?"
        ),
    },
]

def ensure_commercial_seed():
    for p in PRODUCTOS:
        if ProductoCatalogo.query.filter_by(slug=p["slug"]).first():
            continue
        db.session.add(ProductoCatalogo(
            slug=p["slug"],
            nombre=p["nombre"],
            descripcion=p.get("descripcion"),
            precio_mensual_sugerido=p.get("precio_mensual_sugerido", 0),
            setup_sugerido=p.get("setup_sugerido", 0),
            nicho=p.get("nicho"),
            link_landing=p.get("link_landing"),
            planes_json=json.dumps(p.get("planes", []), ensure_ascii=False) if p.get("planes") else None,
        ))
    db.session.commit()

    if not ConfigComision.query.first():
        db.session.add(ConfigComision())
        db.session.commit()

    brand = (os.environ.get("BRAND_COMPANY") or "nuestro equipo").strip() or "nuestro equipo"
    for t in PLANTILLAS_BASE:
        exists = PlantillaMensaje.query.filter_by(
            producto=t["producto"], canal=t["canal"], etapa=t["etapa"]
        ).first()
        if not exists:
            row = dict(t)
            row["cuerpo"] = row["cuerpo"].replace("{{marca}}", brand)
            db.session.add(PlantillaMensaje(**row))
    db.session.commit()
