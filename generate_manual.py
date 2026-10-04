"""Genera el manual PDF del CRM Mi Gestor."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "docs" / "manual-mi-gestor-crm.pdf"


class ManualPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Mi Gestor  |  Página {self.page_no()}", align="C")


def section_title(pdf, text):
    pdf.ln(4)
    pdf.set_font("DejaVu", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(245, 158, 11)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)


def subsection(pdf, text):
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def body(pdf, text):
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(55, 65, 81)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(2)


def bullets(pdf, items):
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(55, 65, 81)
    for item in items:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5.5, f"- {item}")
    pdf.ln(2)


def steps(pdf, items):
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(55, 65, 81)
    for i, item in enumerate(items, 1):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5.5, f"{i}. {item}")
    pdf.ln(2)


def build_pdf():
    pdf = ManualPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_font("DejaVu", "", r"C:\Windows\Fonts\segoeui.ttf")
    pdf.add_font("DejaVu", "B", r"C:\Windows\Fonts\segoeuib.ttf")
    pdf.add_font("DejaVu", "I", r"C:\Windows\Fonts\segoeuii.ttf")

    # Portada
    pdf.add_page()
    pdf.ln(35)
    pdf.set_font("DejaVu", "B", 26)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 14, "Mi Gestor", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 10, "Manual de uso — CRM de ventas", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("DejaVu", "", 11)
    pdf.cell(0, 8, "CRM de ventas", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("DejaVu", "I", 10)
    pdf.multi_cell(
        0,
        6,
        "Guía simple para el equipo comercial: clientes, prospectos, redes sociales y proyectos.",
        align="C",
    )

    # 1. Acceso
    pdf.add_page()
    section_title(pdf, "1. Cómo entrar")
    body(
        pdf,
        "Mi Gestor es el CRM de ventas. Solo el equipo autorizado puede acceder.",
    )
    subsection(pdf, "Dirección web")
    bullets(
        pdf,
        [
            "Abre la dirección del CRM y entra por /login",
            "Ejemplo: tudominio.cl/login",
        ],
    )
    subsection(pdf, "Credenciales")
    bullets(
        pdf,
        [
            "La cuenta del propietario se crea en /setup la primera vez",
            "No dejes esas credenciales escritas en manuales ni en el repositorio",
        ],
    )
    body(pdf, "Para salir, usa el botón Salir arriba a la derecha.")

    # 2. Navegación
    section_title(pdf, "2. Menú principal")
    body(pdf, "Arriba verás las secciones del CRM:")
    bullets(
        pdf,
        [
            "Dashboard — tu resumen del día",
            "Proyectos — seguimiento de trabajos con clientes",
            "Clientes — agenda comercial y seguimientos",
            "Prospectos IA — leads nuevos y mensajes de contacto",
            "Redes — contenido para Instagram, TikTok, etc.",
            "Instagram / TikTok / Calendario — accesos directos a redes",
        ],
    )
    subsection(pdf, "Botones útiles (barra superior)")
    bullets(
        pdf,
        [
            "Buscar (Ctrl+K) — encuentra clientes, proyectos o posts al instante",
            "Instalar — convierte el CRM en app en el celular o computador",
            "Salir — cierra tu sesión",
        ],
    )
    subsection(pdf, "Botón flotante + (esquina inferior)")
    body(
        pdf,
        "Desde cualquier pantalla puedes crear algo rápido sin perder tu lugar:",
    )
    bullets(
        pdf,
        [
            "Cliente (tecla C)",
            "Proyecto (tecla P)",
            "Interacción con cliente (tecla I)",
            "Post / borrador (tecla B)",
            "Tarea de redes — DM, comentar, etc. (tecla D)",
            "Buscar (Ctrl+K)",
        ],
    )

    # 3. Dashboard
    section_title(pdf, "3. Dashboard — tu día en un vistazo")
    body(
        pdf,
        "Es la pantalla de inicio. Te muestra lo más urgente para hoy.",
    )
    bullets(
        pdf,
        [
            "Posts pendientes y los que debes publicar hoy",
            "Posts atrasados (en rojo) — publícalos cuanto antes",
            "Prospectos por contactar — siguientes DMs o seguimientos",
            "Tareas de redes — DMs, comentarios u otras acciones pendientes",
            "Seguimiento de clientes — quién debes volver a contactar esta semana",
        ],
    )
    body(
        pdf,
        "Botones rápidos arriba: Crear post, Clientes, Calendario y Prospectos.",
    )

    # 4. Clientes
    section_title(pdf, "4. Clientes")
    subsection(pdf, "Para qué sirve")
    body(
        pdf,
        "Guarda la información de cada persona o empresa con la que trabajas: teléfono, email, Instagram, notas y estado (prospecto, activo, etc.).",
    )
    subsection(pdf, "Crear un cliente")
    steps(
        pdf,
        [
            "Ve a Clientes > Nuevo cliente, o usa el botón + > Cliente.",
            "Solo el nombre es obligatorio. Puedes agregar teléfono, email y más después.",
            "Guarda y se abrirá la ficha del cliente.",
        ],
    )
    subsection(pdf, "Ficha del cliente")
    bullets(
        pdf,
        [
            "WhatsApp — escribe un mensaje y abre WhatsApp con el texto listo",
            "Interacción — registra una llamada, reunión o mensaje enviado",
            "Crear proyecto — vincula un trabajo nuevo a ese cliente",
            "Editar — actualiza datos cuando cambien",
        ],
    )
    subsection(pdf, "Historial de interacciones")
    body(
        pdf,
        "Cada vez que hablas con un cliente, registra un resumen. Puedes poner una próxima acción con fecha para que el Dashboard te recuerde hacer seguimiento.",
    )

    # 5. Prospectos IA
    section_title(pdf, "5. Prospectos IA")
    subsection(pdf, "Para qué sirve")
    body(
        pdf,
        "Te ayuda a contactar personas nuevas en Instagram (u otras redes). Analiza el perfil y sugiere un mensaje personalizado para el primer DM.",
    )
    subsection(pdf, "Agregar prospectos")
    bullets(
        pdf,
        [
            "Nuevo prospecto — uno a uno, manual",
            "Instagram — importar varios perfiles de Instagram a la vez",
            "CSV — subir una lista desde Excel o Google Sheets",
        ],
    )
    subsection(pdf, "Flujo recomendado por prospecto")
    steps(
        pdf,
        [
            "Abre el prospecto y revisa su perfil (botón Abrir perfil).",
            "Si es Instagram, puedes Revisar últimas publicaciones para ver señales.",
            "Pulsa Analizar con IA: obtienes ideas sobre cómo acercarte.",
            "Pulsa Generar mensaje: crea un borrador de DM listo para copiar.",
            "Envía el DM en Instagram y luego Marcar DM enviado.",
            "Si responde y cierra, usa Convertir a cliente para pasarlo a Clientes.",
        ],
    )
    body(
        pdf,
        "Filtros arriba: Todos, Con mensaje, Contactados, Nuevos.",
    )

    # 6. Redes
    section_title(pdf, "6. Redes sociales")
    subsection(pdf, "Para qué sirve")
    body(
        pdf,
        "Organiza el contenido de Instagram, TikTok, LinkedIn y Facebook. El CRM no publica solo — tú publicas manualmente en cada app, pero aquí tienes todo preparado.",
    )
    subsection(pdf, "Flujo de publicación (4 pasos)")
    steps(
        pdf,
        [
            "Crear — genera texto e imagen con IA, o escribe un borrador",
            "Descargar + copiar — baja la imagen y copia el texto",
            "Publicar en la app — abre Instagram/TikTok y sube el contenido",
            "Marcar hecho — en el CRM indica que ya se publicó",
        ],
    )
    subsection(pdf, "Crear contenido rápido")
    body(
        pdf,
        "En Redes, el formulario Crear contenido rápido te pide una idea o tema. La IA genera el post y puedes programar fecha. También puedes crear desde el botón + > Post.",
    )
    subsection(pdf, "Modo publicación")
    body(
        pdf,
        "Cuando un post está listo, entra a Publicar. Ahí ves los pasos ordenados: descargar imagen, copiar texto, abrir la red social y marcar como publicado.",
    )
    subsection(pdf, "Calendario")
    body(
        pdf,
        "Muestra todos los posts programados en vista mensual. Puedes arrastrar fechas para reprogramar.",
    )
    subsection(pdf, "Instagram y TikTok")
    bullets(
        pdf,
        [
            "Instagram — lista de posts de IG y registro manual de métricas (seguidores, likes)",
            "TikTok — lo mismo para videos de TikTok",
            "Mis fotos — sube imágenes de referencia para que la IA genere contenido con tu estilo",
        ],
    )
    subsection(pdf, "Tareas de redes")
    body(
        pdf,
        "Recuerda DMs pendientes, comentarios o seguimientos. Créalas con + > Tarea redes (DM). Aparecen en el Dashboard.",
    )

    # 7. Proyectos
    section_title(pdf, "7. Proyectos")
    subsection(pdf, "Para qué sirve")
    body(
        pdf,
        "Cuando un cliente contrata un trabajo, creas un proyecto para seguir fechas, tareas y entregas.",
    )
    subsection(pdf, "Formas de crear un proyecto")
    bullets(
        pdf,
        [
            "Rápido — nombre, cliente y fechas básicas",
            "Desde plantilla — elige Sercotec, Corfo, rebranding, etc. y se crean tareas automáticas",
            "Asistente guiado — paso a paso con objetivo, redes y plan de ventas",
        ],
    )
    subsection(pdf, "Dentro de un proyecto")
    bullets(
        pdf,
        [
            "Carta Gantt — barras de tareas que puedes arrastrar para cambiar fechas",
            "Agregar tareas — divide el trabajo en pasos con fechas y % de avance",
            "Vincular posts — los contenidos de redes pueden asociarse al proyecto",
        ],
    )

    # 8. PWA
    section_title(pdf, "8. Instalar como app")
    body(
        pdf,
        "En el celular o computador, pulsa Instalar en la barra superior. El CRM queda como una app en tu pantalla de inicio, sin buscar la URL cada vez.",
    )

    # 9. Rutina diaria
    section_title(pdf, "9. Rutina diaria sugerida")
    steps(
        pdf,
        [
            "Abre el Dashboard y revisa posts de hoy y atrasados.",
            "Publica lo programado (Redes → Publicar).",
            "Contacta 2–3 prospectos con mensaje generado.",
            "Registra interacciones de clientes que hayas atendido.",
            "Revisa seguimientos de la semana y agenda próximas acciones.",
            "Crea borradores para los próximos días en el Calendario.",
        ],
    )

    # 10. Ayuda
    section_title(pdf, "10. Problemas frecuentes")
    bullets(
        pdf,
        [
            "No puedo entrar — revisa usuario y contraseña. Si persiste, avisa al equipo técnico.",
            "La IA no funciona — se necesita configurar OPENROUTER_API_KEY en el servidor. Sin IA, igual puedes usar todo lo demás manualmente.",
            "No carga la página — recarga el navegador o cierra sesión y vuelve a entrar.",
            "¿Borré algo? — los datos están en la base del servidor. Contacta al equipo si necesitas recuperar algo.",
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build_pdf()
    print(f"Manual generado: {path}")
