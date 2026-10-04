BASE_ITEMS = [
    "Recibir logo", "Recibir colores", "Recibir WhatsApp", "Recibir email",
    "Recibir redes sociales", "Recibir textos", "Recibir fotos", "Recibir precios",
    "Recibir horarios", "Configurar landing", "Configurar formulario", "Cargar servicios",
    "Crear usuarios", "Revisar con cliente", "Capacitar cliente", "Activar servicio",
    "Pedir testimonio",
]

PRODUCT_ITEMS = {
    "Agenda de reservas": [
        "Servicios", "Duración por servicio", "Precios", "Profesionales",
        "Horarios", "Políticas de cancelación", "Fotos",
        "Redes del negocio", "Mensaje de presentación", "Link de reserva",
    ],
    "Sitio web": [
        "Logo", "Colores", "Textos de servicios", "Fotos",
        "Dominio", "Formulario de contacto", "Páginas", "Revisión con el cliente",
    ],
}


def checklist_for_product(producto: str) -> list[str]:
    items = list(BASE_ITEMS)
    for key, extra in PRODUCT_ITEMS.items():
        if key.lower() in (producto or "").lower():
            items.extend(extra)
            break
    return items
