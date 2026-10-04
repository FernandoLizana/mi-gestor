from datetime import datetime


PROSPECT_ESTADOS = [
    "nuevo",
    "analizado",
    "mensaje_generado",
    "contactado",
    "respondio",
    "agendo",
    "convertido",
    "descartado",
]


def append_contact_log(prospecto, nota: str, mensaje: str | None = None):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n---\n{stamp} · {nota}\n"
    if mensaje:
        block += mensaje.strip() + "\n"
    prospecto.historial_contacto = (prospecto.historial_contacto or "").strip() + block
    prospecto.ultimo_contacto = datetime.utcnow()
