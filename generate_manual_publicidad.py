"""Genera el manual PDF detallado del módulo Publicidad."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "docs" / "manual-modulo-publicidad.pdf"


class ManualPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Módulo Publicidad — Mi Gestor  |  Página {self.page_no()}", align="C")


def _fonts(pdf):
    pdf.add_font("DejaVu", "", r"C:\Windows\Fonts\segoeui.ttf")
    pdf.add_font("DejaVu", "B", r"C:\Windows\Fonts\segoeuib.ttf")
    pdf.add_font("DejaVu", "I", r"C:\Windows\Fonts\segoeuii.ttf")


def section(pdf, text):
    pdf.ln(3)
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(245, 158, 11)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def sub(pdf, text):
    pdf.set_font("DejaVu", "B", 10.5)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def body(pdf, text):
    pdf.set_font("DejaVu", "", 9.5)
    pdf.set_text_color(55, 65, 81)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5.2, text)
    pdf.ln(1.5)


def bullets(pdf, items):
    pdf.set_font("DejaVu", "", 9.5)
    for item in items:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5.2, f"- {item}")
    pdf.ln(1.5)


def steps(pdf, items):
    pdf.set_font("DejaVu", "", 9.5)
    for i, item in enumerate(items, 1):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5.2, f"{i}. {item}")
    pdf.ln(1.5)


def table_row(pdf, col1, col2, header=False):
    pdf.set_font("DejaVu", "B" if header else "", 9)
    w1 = 52
    w2 = pdf.w - pdf.l_margin - pdf.r_margin - w1
    h = 6
    if header:
        pdf.set_fill_color(238, 242, 255)
    pdf.cell(w1, h, col1, border=1, fill=header)
    pdf.cell(w2, h, col2, border=1, fill=header, new_x="LMARGIN", new_y="NEXT")


def build():
    pdf = ManualPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 16, 16)
    _fonts(pdf)

    # Portada
    pdf.add_page()
    pdf.ln(28)
    pdf.set_font("DejaVu", "B", 24)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, "Módulo Publicidad", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 13)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 9, "Manual detallado de uso", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 7, "Mi Gestor — módulo de publicidad", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(14)
    pdf.set_font("DejaVu", "I", 9.5)
    pdf.multi_cell(
        0, 5.5,
        "Guía paso a paso para crear campañas de contenido desde documentos "
        "y publicaciones creativas con tus propias fotos.",
        align="C",
    )

    # 1. Introducción
    pdf.add_page()
    section(pdf, "1. ¿Qué es el módulo Publicidad?")
    body(
        pdf,
        "Publicidad es una sección del CRM pensada para la chica de ventas y marketing. "
        "Te permite producir mucho contenido para redes sin empezar desde cero cada vez.",
    )
    bullets(
        pdf,
        [
            "Flujo A — Desde documentos: subes PDFs, papers o imágenes y la IA crea 10 a 15 publicaciones.",
            "Flujo B — Estudio creativo: usas tus fotos para cómics, memes, tips, stories y variaciones artísticas.",
            "Todo lo generado queda en Redes como borradores o publicaciones programadas, listos para publicar manualmente.",
        ],
    )
    sub(pdf, "Lo que NO hace")
    bullets(
        pdf,
        [
            "No publica automáticamente en Instagram, TikTok ni otras apps (evita bloqueos y baneos).",
            "Tú descargas/copias el contenido y lo publicas en la app de la red social, como en el flujo normal de Redes.",
        ],
    )

    section(pdf, "2. Requisitos")
    sub(pdf, "Acceso al CRM")
    bullets(
        pdf,
        [
            "URL: tu-dominio/login (o el prefijo definido en CRM_MOUNT_PATH)",
            "La cuenta se crea en /setup la primera vez",
        ],
    )
    sub(pdf, "Inteligencia artificial")
    body(
        pdf,
        "Para generar textos e imágenes necesitas OPENROUTER_API_KEY en el archivo crm/.env del servidor. "
        "Sin esta clave puedes subir materiales, pero no crear publicaciones automáticas.",
    )
    bullets(
        pdf,
        [
            "AI_PROVIDER=openrouter (recomendado para texto e imágenes)",
            "OPENROUTER_API_KEY=tu_clave",
            "Opcional: OPENROUTER_IMAGE_MODEL para el modelo de imágenes",
            "Opcional: OPENROUTER_VISION_MODEL para analizar imágenes subidas como material",
        ],
    )

    section(pdf, "3. Cómo llegar al módulo")
    bullets(
        pdf,
        [
            "Menú superior > Publicidad",
            "Desde Redes > botón Publicidad IA",
            "URL directa: /publicidad",
        ],
    )
    body(
        pdf,
        "La pantalla principal muestra dos tarjetas grandes: Desde documentos y Estudio creativo. "
        "Abajo verás estadísticas de materiales subidos y posts generados.",
    )

    # 2. Desde documentos
    pdf.add_page()
    section(pdf, "4. Flujo A: Desde documentos (detalle)")
    body(
        pdf,
        "Ideal cuando tienes material de estudio, guías, PDFs de cursos, papers, infografías "
        "guardadas como imagen, capturas de apuntes, etc. La IA lee ese contenido y propone "
        "muchas publicaciones distintas para variar el feed.",
    )

    sub(pdf, "4.1 Archivos que puedes subir")
    table_row(pdf, "Formato", "Qué pasa al subir", header=True)
    table_row(pdf, "PDF", "Se extrae el texto automáticamente (hasta 30 páginas).")
    table_row(pdf, "JPG / PNG", "La IA describe la imagen si hay OPENROUTER configurado.")
    table_row(pdf, "Notas (campo texto)", "Se suman al contenido fuente. Muy útil en PDFs escaneados.")

    pdf.ln(3)
    sub(pdf, "4.2 Subir un material — paso a paso")
    steps(
        pdf,
        [
            "Entra a Publicidad > Desde documentos (o Materiales de campaña).",
            "En Subir material nuevo: escribe un título claro (ej: Guía arcanos mayores).",
            "Selecciona el archivo PDF, JPG o PNG.",
            "Opcional: en Notas describe de qué trata, a quién va dirigido y qué quieres destacar.",
            "Pulsa Subir. El sistema procesa el archivo y te lleva a la ficha del material.",
        ],
    )

    sub(pdf, "4.3 La ficha del material")
    body(pdf, "En la ficha verás:")
    bullets(
        pdf,
        [
            "Contenido detectado: texto extraído del PDF o descripción de la imagen.",
            "Vista previa si subiste una imagen.",
            "Tus notas originales.",
            "Formulario Generar publicaciones con IA.",
            "Lista de publicaciones ya creadas desde ese material (si las hay).",
        ],
    )
    sub(pdf, "Si el PDF no tiene texto")
    body(
        pdf,
        "Algunos PDFs son solo fotos escaneadas. En ese caso el sistema avisará que no hay texto extraíble. "
        "Solución: escribe un resumen en Notas al subir, o sube capturas JPG/PNG con descripción manual.",
    )

    sub(pdf, "4.4 Generar 10–15 publicaciones")
    body(pdf, "En la ficha del material, completa el formulario:")
    table_row(pdf, "Campo", "Descripción", header=True)
    table_row(pdf, "Plataforma", "instagram, tiktok, facebook o linkedin.")
    table_row(pdf, "Cantidad", "10, 12 o 15 publicaciones por lote.")
    table_row(pdf, "Tono", "cercano, místico, profesional, divertido o inspiracional.")
    table_row(pdf, "Enfoque extra", "Opcional. Ej: promover lecturas de amor, enfoque luna nueva.")
    table_row(pdf, "Espaciar calendario", "Si está marcado, programa 1 post por día desde mañana a las 10:30.")
    table_row(pdf, "Generar imágenes IA", "Crea imagen para las primeras 5 publicaciones (tarda más).")

    pdf.ln(3)
    sub(pdf, "4.5 Qué crea la IA en cada publicación")
    bullets(
        pdf,
        [
            "Título corto.",
            "Copy listo para copiar y publicar (2–4 párrafos o bullets).",
            "Hashtags sugeridos.",
            "Formato sugerido: post, carrusel, reel o story.",
            "Ángulo: educativo, tip, promo suave, inspiracional, mito, pregunta, etc.",
        ],
    )
    body(
        pdf,
        "Cada publicación es distinta: la IA varía el enfoque para que no repitas el mismo mensaje.",
    )

    sub(pdf, "4.6 Después de generar")
    steps(
        pdf,
        [
            "Aparece un mensaje de confirmación con cuántos borradores se crearon.",
            "Te redirige a la sección Redes.",
            "Si activaste espaciar calendario, los posts quedan como programados (revisa Calendario).",
            "Si no, quedan como borradores para que los edites y programes tú.",
            "Puedes volver al material y generar otro lote (se acumulan más publicaciones).",
        ],
    )

    sub(pdf, "4.7 Eliminar un material")
    body(
        pdf,
        "En la lista de materiales, botón Eliminar en cada tarjeta. "
        "Las publicaciones ya generadas en Redes no se borran solas; solo se elimina el archivo fuente.",
    )

    # 3. Estudio creativo
    pdf.add_page()
    section(pdf, "5. Flujo B: Estudio creativo (detalle)")
    body(
        pdf,
        "Sirve para contenido con más personalidad y variedad visual: cómics, memes, tips con tu estilo, "
        "stories donde apareces tú, o versiones artísticas de tus fotos. Usa las fotos que subiste en Mis fotos.",
    )

    sub(pdf, "5.1 Preparación: subir tus fotos")
    steps(
        pdf,
        [
            "Ve a Redes > Mis fotos (o Publicidad > Estudio y sigue el enlace).",
            "Sube JPG, PNG o WEBP: fotos tuyas, mesa de tarot, servicios, ambiente del consultorio, etc.",
            "Puedes subir varias a la vez.",
            "Vuelve a Publicidad > Estudio creativo.",
        ],
    )

    sub(pdf, "5.2 Los 5 estilos creativos")
    table_row(pdf, "Estilo", "Para qué sirve / formato imagen", header=True)
    table_row(pdf, "Cómic / viñetas", "Historieta 2–4 viñetas. Formato 4:5 (vertical feed).")
    table_row(pdf, "Meme / humor", "Contenido relatable y divertido. Cuadrado 1:1.")
    table_row(pdf, "Tip visual", "Tarjeta con consejo espiritual o de tarot. Cuadrado 1:1.")
    table_row(pdf, "Story personal", "Imagen vertical tipo story con tu foto integrada. 9:16.")
    table_row(pdf, "Variación creativa", "Remix artístico místico de tu foto. Vertical 4:5.")

    pdf.ln(3)
    sub(pdf, "5.3 Crear una publicación creativa — paso a paso")
    steps(
        pdf,
        [
            "Entra a Publicidad > Estudio creativo.",
            "Elige el Estilo creativo según lo que quieras publicar hoy.",
            "Escribe el Tema o idea (ej: señales del universo cuando piensas en alguien).",
            "Elige Plataforma: instagram, tiktok o facebook.",
            "Variaciones: crea 1, 2, 3 o 5 publicaciones distintas del mismo estilo.",
            "Elige el Tono: cercano, místico, divertido o elegante.",
            "Marca al menos una de Tus fotos (obligatorio). Puedes elegir 2 para más referencia.",
            "Deja marcado Generar imagen con IA si quieres visual listo (usa tus fotos como inspiración).",
            "Pulsa Crear publicación creativa. Espera unos segundos (aparece overlay de carga IA).",
        ],
    )

    sub(pdf, "5.4 Qué genera el estudio")
    bullets(
        pdf,
        [
            "Título del post.",
            "Copy completo para publicar.",
            "Hashtags.",
            "Imagen generada (si activaste la opción), inspirada en tus fotos sin copiar el rostro literal.",
            "Todo queda como borrador en Redes, marcado como origen estudio_creativo.",
        ],
    )

    sub(pdf, "5.5 Consejos por estilo")
    bullets(
        pdf,
        [
            "Cómic: usa temas con mini-historia (antes / durante / después de una lectura).",
            "Meme: ideas cotidianas del mundo espiritual que la gente comparta.",
            "Tip: un solo consejo claro por publicación, fácil de leer en 3 segundos.",
            "Story: fotos tuyas expresivas o con cartas en la mano.",
            "Variación: buena para renovar una foto que ya publicaste con look distinto.",
        ],
    )

    # 4. Publicar
    pdf.add_page()
    section(pdf, "6. Publicar lo generado (conexión con Redes)")
    body(
        pdf,
        "Publicidad crea el contenido; Redes es donde lo publicas. El flujo es el mismo para "
        "cualquier borrador, venga de documentos o del estudio creativo.",
    )

    sub(pdf, "6.1 Flujo de publicación manual (4 pasos)")
    steps(
        pdf,
        [
            "Crear — ya lo hizo Publicidad; revisa en Redes.",
            "Descargar + copiar — en Modo publicación: baja la imagen y copia el texto.",
            "Publicar en la app — abre Instagram/TikTok y sube el contenido.",
            "Marcar hecho — en el CRM indica que ya se publicó.",
        ],
    )

    sub(pdf, "6.2 Editar antes de publicar")
    bullets(
        pdf,
        [
            "En Redes, haz clic en cualquier borrador para editarlo.",
            "Puedes cambiar título, copy, hashtags, fecha y plataforma.",
            "Si falta imagen, usa Generar imagen con IA desde la edición del post.",
            "Programa fecha con el botón Programar o arrastra en Calendario.",
        ],
    )

    sub(pdf, "6.3 Calendario editorial")
    body(
        pdf,
        "Menú > Calendario. Si generaste con espaciar calendario, verás un post por día. "
        "Puedes arrastrar eventos para cambiar la fecha. Clic en un evento abre la edición del post.",
    )

    sub(pdf, "6.4 Dashboard")
    body(
        pdf,
        "El Dashboard muestra publicaciones de hoy y atrasadas. Los posts programados desde "
        "Publicidad aparecen ahí cuando llega su fecha.",
    )

    # 5. Casos prácticos
    section(pdf, "7. Casos prácticos")
    sub(pdf, "Caso 1: Tienes un PDF de 20 páginas sobre tarot")
    steps(
        pdf,
        [
            "Sube el PDF con título claro.",
            "Revisa que el contenido detectado tenga texto (si no, agrega notas resumen).",
            "Genera 15 publicaciones, tono cercano, plataforma Instagram.",
            "Activa espaciar calendario → tienes contenido para 15 días.",
            "Cada día: Dashboard > Publicar > copiar y subir a IG.",
        ],
    )

    sub(pdf, "Caso 2: Captura de una infografía en PNG")
    steps(
        pdf,
        [
            "Sube la PNG. La IA describirá la imagen si hay visión configurada.",
            "Agrega notas con el mensaje principal que quieres comunicar.",
            "Genera 10 posts con enfoque extra: tips para principiantes.",
            "Opcional: generar imágenes IA para las primeras 5.",
        ],
    )

    sub(pdf, "Caso 3: Semana de contenido variado con tus fotos")
    steps(
        pdf,
        [
            "Lunes: Estudio > Cómic, tema lectura de cartas, 1 variación.",
            "Martes: Estudio > Meme, tema señales del universo.",
            "Miércoles: Estudio > Tip visual, tema autocuidado.",
            "Jueves: Estudio > Story personal, foto tuya con cartas.",
            "Viernes: Estudio > Variación creativa, remix de tu mejor foto.",
            "Programa cada borrador en Calendario para la semana.",
        ],
    )

    # 6. Buenas prácticas
    section(pdf, "8. Buenas prácticas")
    bullets(
        pdf,
        [
            "Títulos claros en materiales: te ayudan a encontrarlos después.",
            "Notas detalladas en PDFs escaneados o imágenes ambiguas.",
            "Revisa siempre el copy antes de publicar; la IA puede equivocarse.",
            "No marques generar imágenes en lotes grandes si tienes prisa (las 5 primeras tardan).",
            "Combina campañas desde documentos (educativo) con estudio creativo (personal).",
            "Mantén Mis fotos actualizado con imágenes de buena calidad y buena luz.",
            "Varía tonos entre cercano y místico para no sonar repetitiva.",
        ],
    )

    section(pdf, "9. Problemas frecuentes")
    table_row(pdf, "Problema", "Solución", header=True)
    table_row(pdf, "No genera publicaciones", "Revisa OPENROUTER_API_KEY en crm/.env y reinicia la app.")
    table_row(pdf, "PDF sin texto", "Agrega notas al subir o convierte a imagen JPG.")
    table_row(pdf, "Muy pocas publicaciones", "Intenta generar de nuevo; a veces la IA responde incompleto.")
    table_row(pdf, "Estudio sin fotos", "Sube fotos en Redes > Mis fotos primero.")
    table_row(pdf, "Imagen IA falla", "Reintenta; verifica OPENROUTER_IMAGE_MODEL. El texto igual se guarda.")
    table_row(pdf, "Tarda mucho", "Normal con imágenes IA. Desactiva imágenes en lote o genera de a 1 en estudio.")
    table_row(pdf, "No veo Publicidad", "Actualiza la app en el servidor y reinicia Python en cPanel.")

    section(pdf, "10. Resumen de URLs")
    bullets(
        pdf,
        [
            "Hub Publicidad: /publicidad",
            "Materiales: /publicidad/materiales",
            "Estudio creativo: /publicidad/estudio",
            "Mis fotos: /redes/referencias",
            "Redes (borradores): /redes",
            "Calendario: /redes/calendario",
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Manual generado: {path}")
