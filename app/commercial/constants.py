"""Constantes del módulo comercial Mi Gestor."""

PIPELINE_ESTADOS = [
    "Nuevo",
    "Contactado",
    "Respondió",
    "Interesado",
    "Demo agendada",
    "Demo realizada",
    "Propuesta enviada",
    "Negociación",
    "Cerrado ganado",
    "Cerrado perdido",
    "Contactar más adelante",
]

PIPELINE_COLORS = {
    "Nuevo": "#6366f1",
    "Contactado": "#3b82f6",
    "Respondió": "#06b6d4",
    "Interesado": "#14b8a6",
    "Demo agendada": "#f59e0b",
    "Demo realizada": "#f97316",
    "Propuesta enviada": "#a855f7",
    "Negociación": "#ec4899",
    "Cerrado ganado": "#22c55e",
    "Cerrado perdido": "#6b7280",
    "Contactar más adelante": "#94a3b8",
}

PRIORIDADES = ["baja", "media", "alta", "muy alta"]
TEMPERATURAS = ["frio", "tibio", "caliente"]

TIPOS_INTERACCION = [
    "WhatsApp", "Instagram DM", "llamada", "email", "reunión", "demo",
    "propuesta", "nota interna", "seguimiento", "pago", "contrato", "onboarding",
]

IMPORT_COLUMN_ALIASES = {
    "negocio": "nombre_negocio",
    "nombre_negocio": "nombre_negocio",
    "empresa": "nombre_negocio",
    "nombre": "nombre_negocio",
    "contacto": "nombre_contacto",
    "nombre_contacto": "nombre_contacto",
    "nicho": "nicho",
    "producto_interes": "producto_interes",
    "producto": "producto_interes",
    "comuna": "comuna",
    "ciudad": "ciudad",
    "region": "region",
    "direccion": "direccion",
    "instagram": "instagram",
    "facebook": "facebook",
    "tiktok": "tiktok",
    "linkedin": "linkedin",
    "sitio_web": "sitio_web",
    "web": "sitio_web",
    "website": "sitio_web",
    "whatsapp": "whatsapp",
    "telefono": "telefono",
    "tel": "telefono",
    "email": "email",
    "correo": "email",
    "cargo_contacto": "cargo_contacto",
    "cargo": "cargo_contacto",
    "prioridad": "prioridad",
    "estado": "estado_pipeline",
    "estado_pipeline": "estado_pipeline",
    "fuente": "fuente",
    "motivo_encaje": "motivo_encaje",
    "dolor_detectado": "dolor_detectado",
    "mensaje_sugerido": "mensaje_sugerido",
    "notas": "notas",
    "proxima_accion": "proxima_accion",
    "fecha_proximo_seguimiento": "fecha_proximo_seguimiento",
    "ticket_estimado": "monto_oportunidad",
    "mensualidad_estimada": "mensualidad_estimada",
    "setup_estimado": "setup_estimado",
    "url_perfil": "sitio_web",
    "perfil": "sitio_web",
    "localidad": "comuna",
    "descripcion": "notas",
    "pais": "ciudad",
    "categorias": "nicho",
    "otros_contactos": "otros_contactos",
    "producto": "producto_interes",
    "nombre_organizacion": "nombre_negocio",
    "direccion_publica": "direccion",
    "whatsapp_publico": "whatsapp",
    "telefono_publico": "telefono",
    "email_publico": "email",
    "contacto_objetivo": "nombre_contacto",
    "cargo_objetivo": "cargo_contacto",
    "mensaje_inicial_sugerido": "mensaje_sugerido",
    "mensaje_inicial": "mensaje_sugerido",
    "setup_estimado_clp": "setup_estimado",
    "mensualidad_estimada_clp": "mensualidad_estimada",
    "monto_oportunidad_inicial_clp": "monto_oportunidad",
    "monto_oportunidad_clp": "monto_oportunidad",
    "fuente_verificacion": "fuente_verificacion",
    "contacto_url": "contacto_url",
    "instagram_facebook": "instagram",
    "segmento": "segmento",
    "notas_legales": "notas_legales",
    "modulo_para_demo": "modulo_demo",
    "modulos_demo": "modulo_demo",
    "responsable": "responsable",
    "validacion_contacto": "validacion_contacto",
    "calidad_contacto": "validacion_contacto",
    "comision_primera_venta": "comision_primera_venta",
    "comision_alto_ticket": "comision_alto_ticket",
    "tipo_organizacion": "tipo_organizacion",
}

PRODUCT_IMPORT_SLUGS = {
    "agenda": "Agenda de reservas",
    "sitio-web": "Sitio web",
    "campanas": "Campañas",
}

PRODUCT_NAME_ALIASES = {
    "agenda": "Agenda de reservas",
    "reservas": "Agenda de reservas",
    "sitio": "Sitio web",
    "sitio web": "Sitio web",
    "campanas": "Campañas",
    "campañas": "Campañas",
}

PRODUCT_IMPORT_META = {}

MENSAJE_ETAPAS = [
    "primer contacto", "seguimiento 48 horas", "envío de demo",
    "envío de propuesta", "cierre", "reactivación",
]
MENSAJE_CANALES = ["WhatsApp", "Instagram DM", "Email", "Llamada"]

PROPUESTA_ESTADOS = ["borrador", "enviada", "aceptada", "rechazada", "vencida"]
VENTA_ESTADOS_PAGO = ["pendiente", "pagado", "parcial", "atrasado"]
COMISION_ESTADOS = ["pendiente", "aprobada", "pagada", "anulada"]
COMISION_TIPOS = ["base", "alto_ticket", "bono", "ajuste"]

ONBOARDING_ITEM_ESTADOS = ["pendiente", "en proceso", "listo"]
