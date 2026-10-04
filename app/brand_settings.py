import os

CONTENT_TEMPLATES = {
    "luna_nueva": {
        "label": "Luna nueva",
        "tema": "Ritual de luna nueva, intenciones y manifestación consciente",
        "hashtags": "#lunanueva #tarot #ritual #manifestacion #energia",
    },
    "amor": {
        "label": "Lectura de amor",
        "tema": "Lectura de tarot para claridad en el amor y vínculos",
        "hashtags": "#tarotamor #amorpropio #tarot #lecturadetarot",
    },
    "abundancia": {
        "label": "Abundancia",
        "tema": "Limpieza energética y apertura a la abundancia",
        "hashtags": "#abundancia #tarot #limpiezaenergetica #prosperidad",
    },
    "autocuidado": {
        "label": "Autocuidado",
        "tema": "Mensaje de autocuidado espiritual y conexión interior",
        "hashtags": "#autocuidado #tarot #bienestar #espiritualidad",
    },
    "servicio": {
        "label": "Promo lectura",
        "tema": "Invitación suave a agendar lectura de tarot personalizada",
        "hashtags": "#tarot #lecturadetarot #tarotista #agendatulectura",
    },
}


def brand_signature() -> str:
    return (os.environ.get("BRAND_SIGNATURE") or "").strip()


def template_by_key(key: str | None):
    if not key:
        return None
    return CONTENT_TEMPLATES.get(key)
