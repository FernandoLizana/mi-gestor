"""Enriquecimiento de leads sin scraping — solo datos cargados manualmente o CSV."""

from ..branding import brand_company


def enriquecer_cliente(c):
    """Devuelve dict con sugerencias comerciales basadas en campos del cliente."""
    producto = (c.producto_interes or "").lower()
    tiene_ig = bool(c.instagram)
    tiene_wa = bool(c.whatsapp or c.telefono)
    tiene_web = bool(c.sitio_web)
    notas = (c.notas or "").lower()
    nicho = (c.nicho or "").lower()

    prioridad = c.prioridad or "media"
    temperatura = c.temperatura or "frio"
    dolor = c.dolor_detectado
    plan = c.plan_sugerido
    canal = "WhatsApp" if tiene_wa else ("Instagram DM" if tiene_ig else "email")
    objecion = None
    siguiente = "Primer contacto por el canal disponible"

    if "nails" in producto or "uñas" in nicho or "nail" in nicho:
        if tiene_ig and tiene_wa:
            prioridad = "alta"
            temperatura = "caliente"
            dolor = dolor or "Agenda manual por WhatsApp e Instagram sin sistema centralizado"
            plan = plan or "Pro"
            objecion = "Ya tengo agenda en papel / no quiero complicarme"
            siguiente = "Enviar demo de reservas online mencionando su estilo visual en IG"
        elif tiene_ig:
            prioridad = "media"
            temperatura = "tibio"
            dolor = dolor or "Dificultad para convertir seguidores de Instagram en reservas"
            plan = plan or "Starter"
            siguiente = "Pedir WhatsApp y mostrar link de reserva"

    elif "huésped" in producto or "huesped" in producto or "turismo" in nicho or "hostal" in nicho:
        dolor = dolor or "Huéspedes preguntando lo mismo por WhatsApp (WiFi, horarios, normas)"
        plan = plan or "Hostal"
        prioridad = "alta" if tiene_wa else prioridad
        siguiente = "Ofrecer guía QR por habitación"

    elif "beauty" in producto or "estética" in nicho:
        dolor = dolor or "Gestión de citas y recordatorios manuales"
        plan = plan or "Pro"

    elif "delalma" in producto or "alma" in producto or "tarot" in nicho or "espiritual" in nicho:
        dolor = dolor or "Presencia web dispersa; perfil en directorio sin portal propio de reservas"
        plan = plan or "Starter"
        prioridad = "alta" if tiene_web else prioridad
        siguiente = "Ofrecer portal profesional vinculado a su perfil del código ético"
        canal = "email" if not tiene_wa and c.email else canal

    elif tiene_web and not tiene_wa:
        canal = "email"
        siguiente = "Contactar por email con propuesta de mejora del sitio"

    mensaje = c.mensaje_sugerido
    if not mensaje and c.nombre_contacto:
        negocio = c.empresa or c.nombre
        mensaje = (
            f"Hola {c.nombre_contacto.split()[0]}, soy de {brand_company()}. "
            f"Vi {negocio} y creo que {c.producto_interes or 'nuestra solución'} "
            f"podría ayudarte con {dolor or 'tu operación diaria'}. ¿Te parece una llamada breve?"
        )

    return {
        "prioridad": prioridad,
        "temperatura": temperatura,
        "dolor_detectado": dolor,
        "plan_sugerido": plan,
        "canal_recomendado": canal,
        "objecion_probable": objecion,
        "proxima_accion": siguiente,
        "mensaje_sugerido": mensaje,
    }
